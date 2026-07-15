# 8002 Router — Free-Provider Fix (13.07.2026)

## Проблема
8002 роутер падал, когда DeepSeek кончались деньги — потому что ORDER_CHAT включал `deepseek_flash`.
Healthcheck помечал GitHub как dead при 429 (rate limit), и оставался только DeepSeek с пустым балансом.

## Что починили
### 1. ORDER_CHAT — только бесплатные, без DeepSeek
```python
ORDER_CHAT = ["mistral", "github"]  # было: ["mistral", "github", "ollama", "deepseek_flash"]
ORDER_CODE = ["mistral", "github"]
ORDER_CREATIVE = ["mistral", "github"]
```

### 2. GitHub не умирает от 429
После инициализации _state, перезаписываем для ORDER_CHAT: alive=True по умолчанию.

### 3. Мёртвые провайдеры удалены из ORDER_CHAT
- Ollama: 401 Unauthorized
- GigaChat: SSL error (сертификат Сбера)
- Zhipu: 401 token expired
- OpenRouter: 403 Access denied (CloudFlare)

### 4. Живые провайдеры
- Mistral: 3 ключа, бесплатно 500K TPM ✅
- GitHub Models: 2 токена, gpt-4o-mini бесплатно 15 RPM ✅ (иногда 429)

## Файлы
- Роутер: `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`
- Сервис: `zinaida-router.service` (порт 8002)

## Железное правило
8002 — страховочный роутер, полностью независим от DeepSeek.
