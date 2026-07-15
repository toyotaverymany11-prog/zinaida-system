# Deep Research система

**Версия:** 3.0 (11.07.2026)
**Файлы:**
- Ядро: `/opt/zinaida/scripts/deep_research.py`
- Оркестратор: `/opt/zinaida/scripts/deep_research_orchestrator.py`
- Документация: `/opt/zinaida/DEEP_RESEARCH_SYSTEM.md`
- Заставка: `/opt/zinaida/deep_research_splash.html`

## Архитектура (v3 — 11.07.2026)

### 4 агента с РАЗДЕЛЁННЫМИ РОЛЯМИ

| Агент | Модель | Роль | Поисковик | Стоимость |
|-------|--------|------|-----------|-----------|
| **Mistral** | mistral-small-latest | Широкий обзор | **Tavily** | Бесплатно |
| **Mistral2** | mistral-small-latest | Другой угол | **DuckDuckGo** (ddgs) | Бесплатно |
| **GitHub** | gpt-4o-mini | Поиск по серверу | **grep + SQLite** | Бесплатно |
| **Ollama** | **gemma3:4b** | Узкая конкретика | **Tavily** (цифры/даты) | Бесплатно |
| **DeepSeek V3** | deepseek-chat | Синтезатор (только R4+R2) | Нет | ~$0.01 |

### Исправления 11.07.2026
- Ollama: gemma3:27b(платная,падала) → gemma3:4b(бесплатная,~2с)
- Mistral2: дубликат Tavily → DuckDuckGo (другой поисковик)
- GitHub: дубликат Tavily → поиск по серверу (grep+SQLite)
- Ollama: без интернета → Tavily узкий запрос (цифры/даты)
- Fallback: GitHub не ответил → Mistral
- DuckDuckGo важен: `from ddgs import DDGS`, НЕ `DuckDuckGoSearch`

### Парсинг вопросов
DeepSeek НЕ пишет "поисковый запрос:" в оценке. Формат: `**Q2:** ✅ **ГОДНЫЙ**`.
Берём текст вопроса как запрос. Структура: `{agent: {agent, questions}}`.

### Контекстная чистота
Примеры запросов НЕ из проекта "Отношения". Только нейтральные (ИИ, технологии).
