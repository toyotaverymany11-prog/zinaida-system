# Todoist — ключи и конфигурация
## Дата первой фиксации: 17.07.2026

## API
- **Токен:** `4f439c11320a5a046dd84e9133cb3b951a7ee9b4`
- **Endpoint:** `https://api.todoist.com/api/v1/` (НЕ /rest/v1/ — deprecated)
- **Где хранится:** `/opt/zinaida/meta_agent/.env` (`TODOIST_API_TOKEN`)

## Проекты (7 шт, созданы 12.07.2026)
| Название | ID |
|----------|-----|
| Inbox | 6h56jRJW65QCxJFf |
| Стратегия | 6h56qv93FFMMVj5V |
| Контент | 6h56qvGJgxHCxpH3 |
| Техника | 6h56qvJwXHW8hrCX |
| Дизайн | 6h56qvHh7xGwx2VG |
| Встречи | 6h56qvRh3VM4Xjhh |
| Идеи | 6h56qvPFwPr38JMr |

## Память (система на 17.07.2026)
- **MEMORY.md** — 10000 символов (лимит увеличен с 2200)
- **USER.md** — 5000 символов (лимит увеличен с 1375)
- **Holographic** — auto_extract=true, БД: 68 фактов в memory_store.db
- **Mem0** — disabled (был отключён из-за проблем)

## Cron
- **7:00** — ежедневный дайджест задач (cronjob id: 4646987b527f)
- **9:00** — отчёт о выполненных задачах (cronjob id: 5fe85e3a89df)

## Правила (железобетонные)
1. Если токен потеряется — восстанавливать из `/opt/zinaida/vault/keys/todoist.md`
2. НЕ использовать `/rest/v1/` — только `/api/v1/`
3. due_string только на английском (today, tomorrow, next monday)
