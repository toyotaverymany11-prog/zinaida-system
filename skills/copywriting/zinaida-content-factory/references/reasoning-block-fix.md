# Reasoning Block Suppression (Hermes Web UI)

## Problem
Hermes Studio shows "Процесс размышления" / "Thinking" blocks with English reasoning text above the actual response. This frustrates users who only want the answer.

## Root Cause — Two Levels

### Level 1: Hermes Config
`display.show_reasoning: true` in `~/.hermes/config.yaml` — when enabled, Hermes prepends reasoning content to the response.

### Level 2: Router / Model
DeepSeek models (and other reasoning models like Gemini via OpenRouter) return `reasoning_content` in the OpenAI-compatible streaming response. The Hermes Web UI renders this as a separate "Процесс размышления" block even when `show_reasoning: false` is set.

## Fix (Apply Both Levels)

### Level 1: Config
```yaml
display:
  show_reasoning: false
```
Apply: `sed -i 's/show_reasoning: true/show_reasoning: false/' /root/.hermes/config.yaml`
Restart: `systemctl restart hermes-gateway.service`

### Level 2: Router Proxy
In the router (zinaida_openai_proxy.py), filter `reasoning_content` from SSE chunks:

1. Add a helper function:
```python
def _strip_reasoning_from_chunk(chunk: str):
    """Remove reasoning_content/reasoning from SSE chunks."""
    if chunk == "data: [DONE]":
        return chunk
    try:
        data = json.loads(chunk[6:])
        for ch in data.get("choices", []):
            delta = ch.get("delta", {})
            removed = delta.pop("reasoning_content", None) or delta.pop("reasoning", None)
            if removed is not None and not delta.get("content"):
                return None  # drop chunk with reasoning only
        return "data: " + json.dumps(data, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, IndexError):
        return chunk
```

2. Apply in streaming generators — wrap each yielded chunk:
```python
async for chunk in r.aiter_lines():
    if chunk:
        cleaned = _strip_reasoning_from_chunk(chunk)
        if cleaned is not None:
            yield f"{cleaned}\n\n"
```

3. For non-streaming responses, strip `reasoning` from message:
```python
def _strip_reasoning_from_response(result: dict) -> dict:
    for ch in result.get("choices", []):
        msg = ch.get("message", {})
        msg.pop("reasoning", None)
        msg.pop("reasoning_content", None)
    return result
```

## Verification
After both fixes:
1. Check config: `grep show_reasoning ~/.hermes/config.yaml` → should be `false`
2. Check router health: `curl -s http://127.0.0.1:8002/health`
3. Send a test query and verify no "Процесс размышления" block appears
4. The chat footer should show model name only (no reasoning metadata)

## Key Insight
The config fix alone is NOT enough for Hermes Web UI — the Web UI renders `reasoning_content` from the raw model response regardless of the config setting. You MUST strip at the router level too.
