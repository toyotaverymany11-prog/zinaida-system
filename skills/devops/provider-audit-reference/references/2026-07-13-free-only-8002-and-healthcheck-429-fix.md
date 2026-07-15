# 8002 Free-Only Architecture + Healthcheck 429 Fix (13.07.2026)

## Context
13.07.2026 — DeepSeek ran out of money. Oleg demanded 8002 router work completely independently of DeepSeek, using only free providers. 

## Key Changes

### 1. DeepSeek PURGED from 8002 ORDER_CHAT
- Removed `deepseek_flash` and `deepseek_pro` from all ORDER_CHAT lists
- New chain: `["mistral", "github"]` — only verified-live free providers
- Dead providers removed: Ollama (401), GigaChat (SSL), Zhipu (401), OpenRouter (403)

### 2. `FREE_PROVIDERS` removed (no longer needed)
The set `{"mistral", "github", "ollama"}` was deleted. The race-pool logic was rewritten to just take `alive_order[:2]`.

### 3. Healthcheck 429 → GitHub killed bug
**Problem:** `_probe("github")` returns HTTP 429 (rate limit every ~15 min on monitor interval). The function returns `False`, but does NOT call `_mark_dead()`. However, `_is_available()` reads the `alive` flag — which defaults to `False` for ALL providers on startup. Since `_probe` never calls `_mark_alive()` on 429, GitHub stays dead.

**Fix:** Force `_state[name] = {"alive": True, ...}` for all providers in ORDER_CHAT during initialization:

```python
_state: Dict[str, Dict[str, Any]] = { ... }
# Override: ORDER_CHAT providers start alive
for name in ORDER_CHAT:
    _state[name] = {"alive": True, "dead_until": 0.0, "last_error": "", ...}
```

**Residual issue:** Even with this fix, GitHub can still get `_mark_dead("github")` after 3 failed retries (429 → retry 3 times → dead for 120s). This is handled: Mistral takes over when GitHub is rate-limited.

## Verification
- Short query: `POST /v1/chat/completions model=mistral-small-latest` → 200, Mistral responds
- Complex query: `POST /v1/chat/completions model=deepseek-chat` → 200, falls back to Mistral → GitHub
- No DeepSeek calls whatsoever

## Files Changed
- `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`:
  - Lines 158-163: ORDER_CHAT redefined (DeepSeek removed)
  - Lines 175-178: `_state` override for ORDER_CHAT alive=True
  - Lines 727-728: race_pool logic rewritten (FREE_PROVIDERS removed)
