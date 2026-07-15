# Ollama Fallback Proxy — автоматический перебор ключей

Создан 2026-07-08 после получения 3-го ключа от Олега.

## Проблема
Ollama Cloud ключи могут протухать или превышать лимиты. Ручная смена ключа в конфиге — долго.

## Решение
Прокси-сервер на localhost:8900, который при 401/tаймауте пробует следующий ключ.

## Скрипт
`/opt/zinaida/scripts/ollama_fallback_proxy.py`

Архитектура:
- Python aiohttp сервер
- Принимает POST /v1/chat/completions и /chat/completions
- Пробует ключи по порядку: KEY_1 → KEY_2 → KEY_3
- При 401/tаймауте/ClientError → следующий ключ
- Если все 401 → 503

Читает ключи из `/opt/zinaida/config/secrets.env` (парсит файл построчно).

## Systemd-сервис
`/etc/systemd/system/ollama-proxy.service`
```
[Unit]
Description=Ollama Fallback Proxy
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/zinaida/scripts/ollama_fallback_proxy.py
WorkingDirectory=/opt/zinaida
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Команды:
```bash
systemctl enable ollama-proxy.service
systemctl start ollama-proxy.service
systemctl status ollama-proxy.service
```

## Порты
- Прокси: **8900**
- Проверка: `curl http://127.0.0.1:8900/health`

## Ключи (в secrets.env)
- `OLLAMA_API_KEY_1` — основной
- `OLLAMA_API_KEY_2` — запасной
- `OLLAMA_API_KEY_3` — третий (добавлен последним)

## Hermes конфиг
```yaml
vision:
    provider: ollama
    model: gemma3:27b
    base_url: http://127.0.0.1:8900  # через прокси
    api_key: proxy  # прокси не проверяет api_key
    timeout: 120
```

Также настроено для профиля lera (`~/.hermes/profiles/lera/config.yaml`).

## Важное предостережение
При запуске прокси **не использовать** `nohup ... &` или `&` в foreground-терминале.
Правильный запуск:
```bash
# Через systemd (постоянно):
systemctl restart ollama-proxy.service

# Для теста (background через terminal tool):
# Флаг background=true, команда БЕЗ & и nohup
```
