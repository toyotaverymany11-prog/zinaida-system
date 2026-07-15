# Provider Audit — 2026-07-11

## Actual State (Tested Live)

| Provider | Endpoint | Status | Note |
|----------|----------|--------|------|
| **Zina2-Router** (8003) | `127.0.0.1:8003/v1` | ✅ Works | DeepSeek V4 Flash, 1M context |
| Zinaida-Router (8002) | `127.0.0.1:8002/v1` | ⚠️ Responds but empty content | Keys inside expired |
| OpenRouter (3 keys) | `openrouter.ai/api/v1` | ❌ 403 Forbidden | Server IP blocked, not key issue |
| GitHub Models | `models.inference.ai.azure.com` | ❌ 401 Bad credentials | Token expired |
| GitHub Copilot | `api.githubcopilot.com` | ❌ 403 Forbidden | Token expired |
| DeepSeek direct | `api.deepseek.com/v1` | ❌ 401 invalid key | Key expired |
| Mistral (3 keys) | `api.mistral.ai` | ❌ 401 Unauthorized | All 3 expired |
| Nous Portal | `inference-api.nousresearch.com` | ❌ Key expired | Oleg can get new one free |

## Root Cause

All API keys were obtained months ago and expired. No auto-refresh mechanism.
OpenRouter 403 is server-IP-level — even new keys from this server get 403.

## Fix Priority

1. **DeepSeek** — fastest fix. New key at `api.deepseek.com`. Replaces expired `sk-f50...0eca`.
2. **Nous Portal** — free. Oleg gets new key. Has Claude Opus 4.8, GPT-5.5.
3. **Mistral** — new key at `console.mistral.ai`.
4. **GitHub Models** — new PAT with `models:read` scope.

## Until Fixed

Use Zina2-Router (8003) with `model: Zina2-Router` — works but DeepSeek V4 Flash outputs `reasoning_content` instead of `content` when reasoning mode is on. To get clean output, disable reasoning or use model without reasoning.
