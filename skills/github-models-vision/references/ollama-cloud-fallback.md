# Ollama Cloud — основной vision-провайдер Зинаиды (с 2026-07-08)

## Статус
GitHub Models vision заменён на Ollama Cloud из-за 401 Unauthorized.
Ollama Fallback Proxy (порт 8900, systemd-сервис) перебирает 3 ключа при ошибках.

## Параметры API
```
Базовый URL (прокси): http://127.0.0.1:8900
Прямой URL:           https://ollama.com/v1
Эндпоинт чата:        POST /v1/chat/completions (или /chat/completions)
Список моделей:       GET /v1/models
Авторизация:          Authorization: Bearer {ключ}
Формат:               OpenAI-совместимый
```

## Ollama Fallback Proxy — архитектура

```
Hermes vision_analyze
       ↓
POST http://127.0.0.1:8900/{v1/}chat/completions
       ↓
Ollama Fallback Proxy (python3, aiohttp)
       ↓ пробует ключи по порядку
OLLAMA_API_KEY_1 → если 401 → OLLAMA_API_KEY_2 → если 401 → OLLAMA_API_KEY_3
       ↓
https://ollama.com/v1/chat/completions
```

**Скрипт:** `/opt/zinaida/scripts/ollama_fallback_proxy.py`
**Systemd:** `ollama-proxy.service` (enabled, auto-restart)
**Порт:** 8900 (127.0.0.1)
**Ключи:** читает из `/opt/zinaida/config/secrets.env` на старте

## Конфигурация Hermes (оба профиля)

```yaml
vision:
    provider: ollama
    model: gemma3:27b
    base_url: http://127.0.0.1:8900   # ЧЕРЕЗ ПРОКСИ, не напрямую
    api_key: proxy
    timeout: 120
```

## Где лежат ключи
- `/opt/zinaida/config/secrets.env`
- `OLLAMA_API_KEY_1` — основной
- `OLLAMA_API_KEY_2` — запасной
- `OLLAMA_API_KEY_3` — третий

## Диагностика
- Проверка прокси: `curl http://127.0.0.1:8900/health` → `{"status":"ok","keys":3}`
- Проверка сервиса: `systemctl status ollama-proxy.service`
- Логи: `journalctl -u ollama-proxy.service --no-pager -n 20`
