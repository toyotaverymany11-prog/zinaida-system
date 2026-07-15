---
name: todoist-planner
description: "Полноценный планировщик на Todoist. Создание, отслеживание, напоминание задач. Telegram уведомления. Интеграция с Hermes и Mem0. API v1."
version: 2.0.0
author: Zinaida
tags: [планировщик, todoist, задачи, напоминания, telegram, cron]
related_skills: [zinaida-promise-protocol]
---

# Todoist Planner — планировщик задач

## Триггер
Олег говорит «планировщик», «напомни», «запиши задачу», «что я должен сделать», «что не доделал» → загрузить этот навык.

## Архитектура
```
Олег (чат) → Я (Зинаида) → Todoist API (REST v1) → задачи
                          → Telegram (send_message) → уведомления
                          → Mem0 (add_memory) → контекст задач
                          → cronjob → ежедневный дайджест в 7:00
```

## ⚠️ API v1 — верный endpoint (ПРОВЕРЕНО 13.07.2026)
**REST v1 НЕ РАБОТАЕТ на `/rest/v1/` — HTTP 410 deprecated!**
**Работает только на `/api/v1/`.**

### Верные endpoint'ы
```http
GET    https://api.todoist.com/api/v1/tasks     — list_tasks
GET    https://api.todoist.com/api/v1/projects  — list_projects
POST   https://api.todoist.com/api/v1/tasks     — create_task
POST   https://api.todoist.com/api/v1/tasks/:id/close
```

### Ответы v1
- Возвращают **dict с ключом `results`**, не массив как раньше
- Пример: `data.get('results', [])`
- Есть ключ `next_cursor` для пагинации

### Подробно
Подробная документация и все питфоллы: `references/api-docs.md`

## Питфоллы (документировано 12.07.2026)
- `due_string="this week"` — HTTP 400 Invalid date format
- due_string с кириллицей — не работает
- Работает только: `due_date="2026-07-16"` (ISO дата) или `due_string` на английском "today", "tomorrow", "next monday"
- Приоритеты: `priority=1` в API = красный (p4 в UI), `priority=4` = обычный (p1 в UI)
- Приоритеты в api.create_reminder: p1(красный) для важных событий (врач), p2(оранж) для обычных

### 🚨 ЖЁСТКОЕ ПРАВИЛО: УВЕДОМЛЕНИЕ ЗА ЧАС, НЕ МИНУТА В МИНУТУ (добавлено 13.07.2026)
Олег явно сказал: **напоминание должно приходить за час до события, а не в момент**. 
Todoist due_string: `tomorrow at 10:15` для события в 11:15, а не `tomorrow at 11:15`.
Telegram — отдельное уведомление утром (7:00) если событие днём.
Никогда не ставить `due_string` на точное время события.

### 🔔 Напоминания в Telegram (добавлено 13.07.2026)

Олег хочет получать напоминания о событиях в Telegram. Схема:

```
Олег (любой чат) → "запомни завтра в 11:15 к гастроэнтерологу"
  ↓
1. Создаётся задача в Todoist (проект «Встречи»)
2. Создаются ДВА cron-уведомления:
   а) В 7:00 утра в день события — «Сегодня в 11:15 прием у...»
   б) За 1 час до события — «Через час к... В 11:15. Пора собираться!»
   НИКОГДА не минута в минуту. НИКОГДА не за 2 часа. За час.
3. Запись в /opt/zinaida/shared_memory/events.json с полем remind_before: 60
```

**Работает из любого чата** (веб Hermes Studio). Триггер-слова: «запомни», «напомни», «создай событие».

**Скрипт:** `/opt/zinaida/scripts/scheduler.py`

```python
# Добавить событие (Todoist + cron + events.json)
python3 /opt/zinaida/scripts/scheduler.py add "завтра в 11:20 прием у хирурга"

# Список предстоящих
python3 /opt/zinaida/scripts/scheduler.py list
```

**Важно:** 
- Todoist уведомляет в приложении Т в **due time**. Если поставить `due_string="tomorrow at 11:15"` — уведомление придёт в 11:15, минута в минуту (Олег: «блядь минута в минуту на хуй»). **Фикс:** ставить `due_string="tomorrow at 10:15"` (за 1 час до события).
- Telegram уведомление в 7:00 — отдельный cron, не связано с Todoist.
- Время всегда московское (MSK).

## Эффективные контексты ввода

- «запомни завтра в 11:20 прием у хирурга» — Todoist due на 10:20 (за час), Telegram cron в 7:00
- «напомни через 2 часа созвон» — через 2 часа
- «создай событие завтра в 9:00 позвонить клиенту» — завтра 9:00
- «запомни сегодня в 15:00 встреча» — сегодня

## ID проектов (созданы 12.07.2026)
Стратегия: `6h56qv93FFMMVj5V`
Контент: `6h56qvGJgxHCxpH3`
Техника: `6h56qvJwXHW8hrCX`
Дизайн: `6h56qvHh7xGwx2VG`
Встречи: `6h56qvRh3VM4Xjhh`
Идеи: `6h56qvPFwPr38JMr`

## ИНИЦИАТИВА (что делаю сама, без команды)
1. Приняли решение → create_task + "записал"
2. Олег сказал «надо бы / хорошо бы / давай потом» → create_task в Идеи p3-p4 + "записал в планировщик"
3. Вижу паттерн (3+ однотипных) → create_task в Стратегия + "тут система, давай обсудим"
4. После каждого важного решения → add_memory в Mem0 + create_task в Todoist
5. Каждое утро 7:00 → дайджест в Telegram (cronjob no_agent=True)
6. Задача просрочена → напоминаю в чате / Telegram
7. Олег сказал «занеси / запиши / зафиксируй» → сразу create_task + "сделано"

## Приоритеты
- p1 (красный, priority=1) — срочно/горим/важно
- p2 (оранж, priority=2) — надо сделать/запланировано
- p3 (синий, priority=3) — хорошо бы/идея
- p4 (серый, priority=4) — когда-нибудь/отложено

## Файлы
- `/opt/zinaida/todoist_integration/todoist_api.py` — Python API (⚠ использует /api/v1/, проверить если старый код ещё на /rest/v1/)
- `/opt/zinaida/todoist_integration/todoist_v1_client.py` — (если создан) верный клиент на /api/v1/
- `/opt/zinaida/todoist_integration/daily_digest.py` — скрипт дайджеста
- `/opt/zinaida/.env` — TODOIST_API_TOKEN
- `/root/.hermes/scripts/daily_digest.py` — копия для cronjob
- `/opt/zinaida/scripts/scheduler.py` — планировщик (создание событий + напоминания в Telegram + Todoist)
- `/opt/zinaida/shared_memory/events.json` — хранилище событий
- `references/api-docs.md` — полная документация API и питфоллы

## Cron
- Job ID: `528f10bcd337` — ежедневно 7:00, no_agent=True, script=daily_digest.py

## Диагностика
```bash
python3 /opt/zinaida/todoist_integration/todoist_api.py status
```
Выведет список проектов, количество задач.
