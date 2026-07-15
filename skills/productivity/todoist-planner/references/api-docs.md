# Todoist API v1 — тестировано 12.07.2026
Источник: https://developer.todoist.com/api/v1/

## REST v1 (работает — ПРОВЕРЕНО 13.07.2026)
**⚠ ВАЖНО: URL prefix изменился!**
- `/rest/v1/*` — HTTP 410 (deprecated, больше не работает)
- `/api/v1/*` — работает, верный endpoint

### Верные endpoint'ы
```
POST   /api/v1/tasks              — create_task {content, project_id, priority, due_date, due_string, description, labels}
POST   /api/v1/tasks/:id/close    — закрыть задачу
POST   /api/v1/tasks/:id/reopen   — открыть заново
DELETE /api/v1/tasks/:id          — удалить
GET    /api/v1/tasks              — list_tasks (params: project_id, filter, limit)
GET    /api/v1/projects           — list_projects
POST   /api/v1/projects           — create_project {name}
```

### Питфоллы (добавлено 13.07.2026)
- `/rest/v1/*` — HTTP 410 (⚠ старый навык ссылался на /rest/v1/, это больше НЕ РАБОТАЕТ)
- `/api/v1/*` — единственный рабочий prefix (проверено на проектах, задачах)
- Синхрон API (sync/v9/*) — тоже HTTP 410, используем REST v1
- due_string="this week" — не работает, 400 Invalid date format
- due_string с кириллицей — не работает
- Работает: due_date="2026-07-16" (ISO дата)
- Приоритеты: 1=p4(красный), 2=p3, 3=p2, 4=p1(обычный)

### Ответ v1 — формат dict, не list
- GET /api/v1/projects и /api/v1/tasks возвращают **dict с ключом "results"**
- Не list, как было в старом REST API
- Пример: `data.get('results', [])` для получения массива
- Есть также ключ `next_cursor` для пагинации

## ID проектов (созданы 12.07.2026)
Стратегия: 6h56qv93FFMMVj5V
Контент: 6h56qvGJgxHCxpH3
Техника: 6h56qvJwXHW8hrCX
Дизайн: 6h56qvHh7xGwx2VG
Встречи: 6h56qvRh3VM4Xjhh
Идеи: 6h56qvPFwPr38JMr
Inbox: 6h56jRJW65QCxJFf
