# 8005 Router Optimization — Case Study (11.07.2026)

## Situation
Zina2 Router v2.0 (`router_8005_v2.py`) — 6-stage pipeline: classification → Mistral pre-processing → RAG → DeepSeek generation → Mistral verification → GigaChat editing. Complaint: «тормозит».

## Diagnosis Steps

### 1. Check if service is actually running
```bash
ss -tlnp | grep 8005
# → empty! Service NOT started.
```

Lesson: `curl` to port returns `000` but doesn't tell *why*. `ss -tlnp` immediately shows which process (or absence) is listening.

### 2. Start and measure baseline
```bash
# Health check — validate all keys loaded
curl -s http://127.0.0.1:8005/health
# → deepseek_key_preview: sk-f500991..., mistral_keys: 3, gigachat: true

# Simple request timing
time curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"Привет как дела"}]}' 2>&1 | tail -1
# → TIME_REAL=1.78s

# Long request timing (content post)
time curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"Напиши пост про мужскую психологию..."}]}' 2>&1 | tail -1
# → TIME_REAL=4.51s
```

### 3. Analyse each pipeline stage
Read the code, identify each stage:

| Stage | Function | Est. time | Action |
|-------|----------|-----------|--------|
| Classification | `_classify_request()` | <5ms | Local, no network |
| Mistral pre-process | `_preprocess_query()` | +1-3s | API call to Mistral |
| RAG search | `_search_rag()` | <50ms | Local SQLite |
| DeepSeek generation | `_call_deepseek()` | +2-4s | Main API call |
| Mistral verification | `_verify_response()` | +1-3s | Parallel API call |
| GigaChat polish | `_polish_response()` | +3-4s | API call + **3s rate limit pause** |

### 4. Isolate bottleneck — strip stages incrementally
```python
# 4a. Disable Mistral pre-processing
async def _preprocess_query(text: str) -> str:
    return text  # DeepSeek Flash handles this itself

# 4b. Disable GigaChat polish
polished_text = response_text  # Skip GigaChat entirely

# 4c. Disable Mistral verification (no longer parallel-relevant)
# Just don't create verify_task
```

### 5. Measure after optimization
```
Before: 4.5s on long post
After:  4.6s — nearly identical!
```

### 6. Compare with sibling service (8003 bare DeepSeek)
```bash
time curl -X POST http://127.0.0.1:8003/v1/chat/completions \
  -d '{"model":"Zina2-Router","messages":[{"role":"user","content":"same request"}]}' 2>&1 | tail -1
# → TIME_REAL=6.3s
```

**Conclusion:** 8005 was **faster** than 8003 despite pipeline overhead. The real bottleneck was DeepSeek API latency (4-5s), not the extra pipeline stages.

### 7. Create systemd service
```bash
cat > /etc/systemd/system/zina2-router-8005.service << 'SYSTEMD'
[Unit]
Description=Zina2 Router v2.0 — DeepSeek + 5 усилителей (Port 8005)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/zinaida/meta_agent
ExecStart=/usr/bin/python3 /opt/zinaida/meta_agent/router_8005_v2.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable zina2-router-8005.service
systemctl start zina2-router-8005.service
```

## Key Takeaways
1. **Always start with `ss -tlnp | grep port`** before `curl` — tells you if the service is running at all, not just what it returns
2. **Pipeline bottleneck may be DeepSeek API, not your extra stages** — measure bare DeepSeek first, then add layers
3. **Compare with sibling services** — if 8003 (bare) is slower than 8005 (layered pipeline), the pipeline is not the problem
4. **GigaChat rate limit (3s between requests)** — kills speed on every request, even parallel. Disable if speed > editing quality
5. **Systemd for new services:** create service → `daemon-reload` → `enable` → `start`. No more manual `python3 ... &`
