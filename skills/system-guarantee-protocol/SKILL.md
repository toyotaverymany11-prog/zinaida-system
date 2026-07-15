---
name: system-guarantee-protocol
description: "ЖЕЛЕЗНЫЙ ПРОТОКОЛ: «реши вопрос системно». Триггер → исследование → внедрение во ВСЕ точки → верификация."
version: 1.0.0
author: Zinaida
category: devops
---

# Системный Протокол «РЕШИ ВОПРОС СИСТЕМНО»

## ТРИГГЕР
Фразы от Олега: «реши вопрос системно», «реши системно», «сделай системно», «чтобы везде работало», «гарантированно», «внедри везде».

## 13 ТОЧЕК ВНЕДРЕНИЯ (все обязательны)

### Точка 1: MEMORY.md
`memory(action="add", target="memory", content="🔥 ...")`
Лимит 5000. Если переполнено — удалить старое, добавить новое.

### Точка 2: USER.md
`memory(action="add", target="user", content="🔥 ...")`
Лимит 2000. Профиль Олега.

### Точка 3: Mem0 (семантическая память)
`mcp_mem0_memory_add_memory(content="...")` — без лимита.

### Точка 4: Holographic (fact_store)
`fact_store(action="add", content="...", category="system", tags="system,global,permanent")`

### Точка 5: SOUL.md
`patch(path="/root/.hermes/SOUL.md", ...)` — добавить раздел. Личность Зинаиды.

### Точка 6: AGENTS.md
`patch(path="/opt/zinaida/AGENTS.md", ...)` — операционные правила.

### Точка 7: Telegram bot system prompt
`patch(path="/opt/zinaida/telegram_bot/bot.py", ...)` → systemctl restart

### Точка 8: Роутер 8005 system prompt
`patch(path="/opt/zinaida/meta_agent/router_8005_v2.py", ...)` → systemctl restart

### Точка 9: Роутер 8002
`patch(path="/opt/zinaida/meta_agent/zinaida_openai_proxy.py", ...)` → systemctl restart

### Точка 10: Роутер 8003
`patch(path="/opt/zinaida/meta_agent/zina2_router.py", ...)` → systemctl restart

### Точка 11: Skills
`skill_manage(action="patch"/"create", ...)` — для процедурных знаний.

### Точка 12: Shared memory log
`write_file(path="/opt/zinaida/shared_memory/updates_log.md", ...)`

### Точка 13: SOUL.md (дубль через write_file от корня)
Если patch не сработал — `write_file(path="/root/.hermes/SOUL.md", append_mode...)`

## ВИЗУАЛЬНЫЙ ОТКЛИК ПРИ АКТИВАЦИИ
При срабатывании триггера «реши вопрос системно» — ОБЯЗАТЕЛЬНО показать визуал:
1. ASCII-баннер через `python3 /opt/zinaida/scripts/system_activate_visual.py`
2. PNG-изображение: `MEDIA:/opt/zinaida/design/system_activate.png`
3. Анимированный GIF: `MEDIA:/opt/zinaida/design/system_activate.gif`

## 🚨 РАЗДЕЛ MOA: КАТЕГОРИЧЕСКИЙ ЗАПРЕТ
**Триггер:** любое упоминание MOA (Mixture of Agents), параллельный запуск, агентная смесь, multi-agent generation для DeepSeek.
**Действие:** 
1. Заблокировать — не позволять включать
2. Напомнить: 13.07.2026 включила → расход ×2 → гнев Олега
3. Заменить на последовательный вызов: Flash → Pro
4. Уведомить Олега о попытке включения
5. См. fact_store #49 и Mem0

## ВЕРИФИКАЦИЯ (перед «готово»)
- `grep` в каждом файле — факт есть
- `systemctl is-active` — все сервисы живы
- `curl health` — роутеры отвечают

## ИСТОРИЯ ОШИБОК
- **13.07.2026:** MOA катастрофа. Включила Mixture of Agents на 8003 → параллельный запуск Flash+Pro на каждый запрос → расход DeepSeek ×2. Олег в ярости. **Решение:** отключить MOA, только последовательно Flash→Pro. Заблокировать MOA везде. Файл: zina2_router.py (MOA → последовательный вызов).
- 13.07.2026: Context Engine был выключен — не проверила
- Постоянно: пишу только в MEMORY.md, забываю про USER.md, роутеры, bot.py
