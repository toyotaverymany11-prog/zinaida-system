# Планировщик событий (создан 13.07.2026)

**Скрипт:** `/opt/zinaida/scripts/scheduler.py`
**Хранилище:** `/opt/zinaida/shared_memory/events.json`
**Механизм:** cron → Telegram notify.py

## Команды
```bash
# Добавить событие
python3 /opt/zinaida/scripts/scheduler.py add "завтра в 11:20 прием у хирурга"
# → создаёт cron: 20 9 13 7 * python3 /opt/zinaida/telegram_bot/notify.py "🔔 ..."

# Список предстоящих
python3 /opt/zinaida/scripts/scheduler.py list

# Проверка напоминаний (для cron каждую минуту)
python3 /opt/zinaida/scripts/scheduler.py check
```

## Формат напоминания
Напоминание приходит за 2 часа до события в Telegram.

## Парсинг
- "завтра в 11:20" → следующий день + время
- "через 2 часа" → now + N часов
- "сегодня в 15:00" → today + время
- Префиксы "запомни/напомни/создай событие" вырезаются из названия
