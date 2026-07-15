# Hermes Built-in Memory Optimization (11.07.2026)

## Результаты глубокого исследования

### Архитектура (4 уровня памяти)
| Уровень | Компонент | Назначение | Лимит |
|---------|-----------|------------|-------|
| Tier 1 (горячая) | MEMORY.md + USER.md | Ключевые факты, профиль | 5000/2000 chars |
| Tier 2 (холодный поиск) | session_search + SQLite FTS | Архив сессий | Не ограничен |
| Tier 3 (внешние провайдеры) | Mem0 | Долговременная, семантический поиск | Внешняя БД |
| Tier 4 (код) | Skills | Процедурное знание | Безлимит, не жрёт контекст |

### Оптимальные лимиты для DeepSeek V4 Flash
- MEMORY.md: 5000 символов (~12% контекста)
- USER.md: 2000 символов (~5% контекста)
- Итого фиксированная часть: ~20% контекста
- На диалог: ~80%

### Команды
```bash
hermes config set memory.memory_char_limit 5000
hermes config set memory.user_char_limit 2000
```

### Источники
- Документация: hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Deep research отчёт: /opt/zinaida/sandbox/deep_research/20260711_115717_.../final_report.md
