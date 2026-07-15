# Vision Proxy Architecture

Файл: `/opt/zinaida/scripts/vision_fallback_proxy.py`
Порт: **8901**
Systemd: `vision-proxy.service`

## Цепочка fallback
1. **GitHub Models** (gpt-4o-mini) - endpoint `https://models.github.ai/inference/chat/completions`
2. **Mistral** (mistral-large-latest) - endpoint `https://api.mistral.ai/v1/chat/completions`
3. **Ollama Cloud** (gemma3:27b, 3 ключа) - endpoint `https://ollama.com/v1/chat/completions`

## Тест трёх моделей (одинаковая картинка)
| Модель | Время | Длина ответа | Детальность |
|--------|------|-------------|-------------|
| GitHub (gpt-4o-mini) | 10.3 сек | 1230 символов | Увидел название, поля, настройки |
| Mistral (mistral-large) | 18.4 сек | 1640 символов | 5 деталей, самый подробный |
| Gemma 3 27B (Ollama) | 20.9 сек | 1432 символов | Хорошее общее описание |

## Mistral quirks
- `mistral-large-latest` supports vision natively (image_url in content array)
- `pixtral-large-latest` does NOT exist (returns 400)
- **Brotli encoding problem:** Mistral returns brotli-compressed responses.
  **Fix:** Use `Accept-Encoding: identity` header (not `deflate, gzip`). This disables all compression and returns raw JSON.
  Both urllib and aiohttp work with this.
- Two keys available: MISTRAL_API_KEY, MISTRAL_API_KEY_2 (for rate limit rotation)

## Ollama quirks
- 3 keys for rate limit rotation
- Large PNGs (>1MB) cause "invalid JSON" - proxy auto-converts to JPEG, resizes to 1024px
- gemma3:27b only vision model on free tier

## GitHub quirks
- Requires PAT with `models:read` scope
- `gpt-4o-mini` may return 404 if wrong endpoint URL
- Correct endpoint: `https://models.github.ai/inference/chat/completions`

## User preferences embedded in this skill
- When generating images, ALWAYS solicit Oleg's opinion afterwards
- Save feedback to `/opt/zinaida/shared_memory/design_feedback.md`
- One final result, no intermediate updates
