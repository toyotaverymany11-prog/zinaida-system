# Scheduler Integration — 13.07.2026

## Что сделано
Создан `/opt/zinaida/scripts/scheduler.py` — скрипт планировщика, который:
1. Парсит текст события ("завтра в 11:20 прием у хирурга")
2. Создаёт задачу в Todoist (проект Встречи)
3. Создаёт cron задачу с напоминанием в Telegram
4. Сохраняет в `/opt/zinaida/shared_memory/events.json`

## Триггер из любого чата
Любой агент (в вебе или Telegram) может выполнить:
```python
import subprocess
subprocess.run(["python3", "/opt/zinaida/scripts/scheduler.py", "add", "завтра в 11:20 прием у хирурга"])
```

## Формат напоминания в Telegram
```
python3 /opt/zinaida/telegram_bot/notify.py "🔔 Напоминание: {title} в {time}"
```
Приходит через cron за 2 часа до события.

## Todoist create_reminder
Использует `api.create_reminder(content=..., when="tomorrow at 11:20", project="Встречи")`.
`when` должен быть на английском: "tomorrow at HH:MM", "today at HH:MM".

## Серверное время
Сервер в MSK: `Europe/Moscow`. Все роутеры знают московское время.
