# Provider Verification Results — 13.07.2026

## Correct test method
Script: `/opt/zinaida/scripts/test_providers_correct.py`
Uses `urllib.request` (not httpx) + direct key reading from `.env`.

## Results

| Provider | Status | Response |
|----------|--------|----------|
| GitHub Models (gpt-4o-mini) | ✅ 200 | "Hello!" |
| Mistral (mistral-small-latest) | ✅ 200 — all 3 keys | "Hi", "Hello" |
| Ollama (gemma3:4b) | ❌ 410/405 all 3 keys | API changed |
| GigaChat (GigaChat:latest) | ❌ 400 | Can't decode Authorization header — key may be expired |
| Zhipu (glm-4-flash) | ✅ 200 | "Hi 👋" |

## Critical finding: httpx vs urllib

**Zhipu** ONLY works via `urllib.request`. httpx.AsyncClient(verify=False) returns 401.
**GigaChat** ONLY works via `urllib.request` + `ssl._create_unverified_context()`. httpx gives 429 or SSL errors.

Lesson: always test providers with `urllib.request` first, not httpx. httpx adds headers that some providers reject.
