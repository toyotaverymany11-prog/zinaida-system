# Telegram bot: переключение провайдера с 8003 на 8005 (12.07.2026)

## Суть
Telegram бот @DCHP_Shtab_bot переключён с `custom:zina2-router` (8003) на `custom:8005` (8005-Router).

## Причина
8003 гнал 99% запросов через DeepSeek Reasoner ($1.42/M) — дорого.
8005 использует Super Cascade: Mistral (бесплатно) → gpt-4o (бесплатно) → DeepSeek Flash/Pro.

## Изменение в bot.py
```python
# Было:
"provider": "custom:zina2-router",
"model": "Zina2-Router"

# Стало:
"provider": "custom:8005",
"model": "8005-Router"
```

## Файл
`/opt/zinaida/telegram_bot/bot.py` — строка 171-172 (константы HERMES_CHAT_RUN payload).

## Рестарт
`systemctl restart zinaida-telegram-bot.service`

## Проверка (логи 8005)
```bash
journalctl -u zina2-router-8005.service --no-pager -n 10 | grep -E "CASCADE|MISTRAL|GITHUB"
```
Должен показывать `MISTRAL CASCADE: уверенность N — ответ готов` или `GITHUB CASCADE: gpt-4o ответил`.
