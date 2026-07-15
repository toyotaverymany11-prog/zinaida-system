# Mem0 Deep Research Summary

**Date:** 10 July 2026 | **Sources:** 20+ (docs, GitHub, Reddit, blogs, comparison articles)

## Critical Findings Before Production

### 1. 97.8% Junk — Issue #4573 (MOST IMPORTANT)
After 32 days in production: 10,134 entries, 97.8% junk, only 38 clean.
**Root cause:** extraction prompt, NOT the model.
**Fix:** `prompt=` parameter in `add()` with explicit instructions on what to save/ignore.

### 2. Embedding Model Choice for Russian
| Model | DIM | RU Quality | Size |
|-------|-----|-----------|------|
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | Good baseline | 471MB |
| **intfloat/multilingual-e5-base** ✅ | **768** | **Best for RU** | **1.1GB** |
| BAAI/bge-m3 | 1024 | Excellent | 2.2GB |

RECOMMENDED: e5-base (768d) — balance of quality and size.

### 3. Qdrant Config for Production
- `on_disk: True` — survive server reboot
- Snapshot backup: `POST /collections/{name}/snapshots`
- No built-in TTL in Mem0 (issue #5588 — feature request)

### 4. Common Beginner Mistakes
1. embedding_model_dims mismatch → empty results
2. openai provider WITHOUT openai_base_url → hits api.openai.com
3. search(q, user_id=x) in v2.0+ → ValueError (use filters=)
4. No custom prompt → 97.8% junk
5. Weak LLM for extraction → JSON parse errors
6. No threshold → irrelevant results
7. Wrong provider param (deepseek_base_url for openai provider)
8. Changing embedder dims requires recreating Qdrant collection

### 5. Best Config (v2.0.11)
```python
llm: provider=openai, model=deepseek-chat, 
     openai_base_url=http://localhost:8003/v1,
     temperature=0.3, max_tokens=4000
embedder: provider=huggingface, model=intfloat/multilingual-e5-base
vector_store: provider=qdrant, host=localhost, port=6333, 
              on_disk=True, embedding_model_dims=768
```
### 6. Key Links
- https://docs.mem0.ai/
- https://github.com/mem0ai/mem0/issues/4573 (junk filter)
- https://docs.mem0.ai/platform/mem0-mcp
- https://vectorize.io/articles/best-ai-agent-memory-systems
- https://arxiv.org/abs/2504.19413 (Mem0 paper, ECAI 2025)
