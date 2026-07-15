# Telegram Bot Provider Switch: 8003 → 8005 (12.07.2026)

## What happened

Telegram bot `zinaida-telegram-bot.service` was switched from `custom:zina2-router` (8003) to `8005-Router` via `custom:8005` provider.

## Problem

The first attempt used Hermes Gateway's `/api/chat-run/runs` endpoint with `provider: custom:8005, model: 8005-Router`. This returned **HTTP 404** because Gateway does not route `custom:` providers through its chat-run API — only through `GET /available-models`.

## Solution

Changed `bot.py` to call **8005 directly** via OpenAI-compatible API:

```python
# Old (via Gateway — 404):
HERMES_CHAT_RUN = "http://127.0.0.1:8642/api/chat-run/runs"
payload = {"input": msg, "profile": "default", "provider": "custom:8005", "model": "8005-Router"}

# New (direct — 200):
HERMES_DIRECT_URL = "http://127.0.0.1:8005/v1/chat/completions"
payload = {"model": "8005-Router", "messages": [{"role": "user", "content": msg}], "max_tokens": 4096}
```

## Trade-off

Direct access to 8005 bypasses Hermes Studio's session management. Telegram conversations are **single-turn** — no history carried between messages. Web UI chats and Telegram chats are **independent sessions**.

The `/newchat` command in Telegram still works (clears the session_id marker in `tg_sessions.json`), but it's a no-op since 8005 doesn't maintain session state.

## Current architecture (as of 12.07.2026)

```
Telegram → bot.py → http://127.0.0.1:8005/v1/chat/completions
                     → Super Cascade: Ollama → Mistral → GPT-4o → DeepSeek Flash → Pro
```

## Affected files

- `/opt/zinaida/telegram_bot/bot.py` — `send_to_hermes_studio()` function
- `/opt/zinaida/telegram_bot/logs/tg_sessions.json` — session tracking (now cosmetic only)
