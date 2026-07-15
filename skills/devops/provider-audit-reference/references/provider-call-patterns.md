# CRITICAL: Provider-Specific Call Patterns

## Key insight (13.07.2026)

**httpx.AsyncClient(verify=False) is NOT a universal tool for provider testing.**

Different LLM providers accept/reject different HTTP clients:

| Provider | Works with httpx? | Works with urllib? | Notes |
|----------|-------------------|-------------------|-------|
| Mistral | ✅ Yes | ✅ Yes | Both work |
| GitHub Models | ✅ Yes | ✅ Yes | Both work, but 429 rate limit |
| DeepSeek | ✅ Yes | ✅ Yes | Both work |
| **Zhipu** | ❌ 401 | ✅ **200** | httpx adds headers Zhipu rejects |
| **GigaChat** | ❌ 429/SSL | ✅ **200** (with ssl context) | httpx verify=False causes SSL + rate limit |
| Ollama | ❌ 401 | ❌ 401 | Keys dead regardless |

## Diagnosis protocol

Before declaring any provider "dead", test with BOTH httpx AND urllib.request.

```python
# ALWAYS test with urllib first for unknown providers:
import urllib.request, json

def test_provider(url, api_key, model, message="Hi one word"):
    data = json.dumps({"model": model, "messages": [{"role": "user", "content": message}], "max_tokens": 5}).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return f"OK: {resp.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.reason[:60]}"
```

Only if urllib also fails should the provider be considered genuinely dead.
