# Стартовый протокол — чеклист для выполнения
## При запросе «дизайн отношения»

```
1. Определить проект: «дизайн отношения» → проект Отношения

□ ШАГ 1 — design_registry.md:
   read_file("/opt/zinaida/shared_memory/design_registry.md")
   → ✅ Реестр дизайна: [N строк]

□ ШАГ 2 — agentmemory:
   mcp_agentmemory_memory_recall(query="дизайн")
   → ✅ agentmemory: [N записей]

□ ШАГ 3 — Zinaida Memory:
   mcp_zinaida_memory_memory_search(query="дизайн")
   → ✅ Zinaida Memory: [N записей]

□ ШАГ 4 — session_search:
   session_search(query="дизайн отношения")
   → ✅ Сессии: [N шт]

□ ШАГ 5 — design_feedback.md:
   read_file("/opt/zinaida/shared_memory/design_feedback.md")
   → ✅ Feedback: [N строк]

□ ШАГ 6 — МОЁ МНЕНИЕ:
   Анализ опыта + рекомендация + план
```

Формат финального ответа:
```
✅ Реестр дизайна: ...
✅ agentmemory: ...
✅ Zinaida Memory: ...
✅ Сессии: ...
✅ Feedback: ...

МОЁ МНЕНИЕ:
Что уже пробовали для этого проекта
Что сработало / не сработало
Моё мнение: какое направление выбрать
Конкретный план: что делаем сейчас
```
