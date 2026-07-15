# Zinaida-Router Architecture (8002)

Файл: `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`
Версия: 4.0
Автостарт: systemd zinaida-router

## Provider chain (июль 2026)
ORDER_CHAT = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]
ORDER_CODE = same
ORDER_CREATIVE = same

### Провайдеры
| Name | Model | Type | Paid? | Keys source |
|------|-------|------|-------|-------------|
| mistral | mistral-large-latest | openai | Нет | MISTRAL_API_KEY, MISTRAL_API_KEY_2 |
| gigachat | GigaChat (не -Max!) | gigachat (oauth) | Нет | GIGACHAT_AUTH_KEY |
| github | gpt-4.1-mini | openai | Нет | GITHUB_TOKEN |
| zhipu | glm-4-flash | openai | Нет | ZHIPU_API_KEY |
| deepseek_flash | deepseek-v4-flash | openai | Да ($) | DEEPSEEK_API_KEY |
| deepseek_pro | deepseek-v4-pro | openai | Да ($) | DEEPSEEK_API_KEY |

### Ключевые настройки
- `load_env()` читает `/opt/zinaida/.env` - ключи хранятся там
- `PROVIDERS["gigachat"]["model"]` = os.getenv("GIGACHAT_MODEL", "GigaChat") - бесплатно
- GigaChat использует OAuth через get_gigachat_token() - живёт 30 мин
- OpenRouter не в цепочке, но определён как провайдер (dead, 403)

### Проблемы
- Агрессивное сжатие контента: каждое сообщение до 8000 символов, общий лимит 100000
- presence_penalty=0.3, frequency_penalty=0.2 - может делать ответы рваными
- GigaChat-Max раньше был моделью по умолчанию - выдавал 402 Payment Required
