# Agent Roles, Search Sources, and Architecture Updates (11.07.2026)

## Роли агентов (Раунд 1)

| Агент | Роль | Поисковик | Что ищет |
|-------|------|-----------|----------|
| Mistral | tavily_broad | Tavily | Широкий обзор темы, главные факты, общая картина |
| Mistral2 | duckduckgo | DuckDuckGo (ddgs) | Другой поисковик = другие результаты. Бесплатно, без ключа |
| GitHub | server_search | Локальный grep + SQLite | Поиск по /opt/zinaida/ файлам, базам phases.db, smm_rag.db |
| Ollama | tavily_narrow | Tavily | Узкий запрос: цифры, даты, статистика, конкретные данные |

## Поисковые источники

### Tavily (основной)
- API ключ из /root/.hermes/.env
- 1000 запросов/мес бесплатно
- advanced search depth, include_raw_content

### DuckDuckGo (ddgs v9.14.4)
- Бесплатно, без API ключа
- `pip install ddgs`
- Импорт: `from ddgs import DDGS`
- Использование: `DDGS().text(query, max_results=N)`
- Возвращает список dict с полями: title, href, body
- Установлен: pip install ddgs

### Поиск по серверу (server_search)
- grep по /opt/zinaida/ — .md, .txt, .py, .json файлы
- SQLite поиск по phases.db и smm_rag.db
- Извлекает ключевые слова из запроса (первые 3 слова длиннее 3 символов)
- fallback: первые 20 символов запроса

## Важные фиксы (11.07.2026)

### Парсер вопросов (parse_approved_questions)
- Формат оценки DeepSeek: `**Q1:** ❌ **МУСОР**` или `**Q1:** ✅ **ГОДНЫЙ**`
- Формат вопросов от агентов: `**Q1:** текст вопроса` (с ** markdown)
- Парсер сначала собирает все вопросы в all_questions (с очисткой `**`),
  потом парсит оценку по regex: `Q(\d+)\s*[:|]\s*(.*?)(✅|❌)`
- Fallback: группировка строк по Q1/Q2/Q3

### Ollama нестабильна
- gemma3:27b через ollama.com/v1 периодически не отвечает
- Проблема: API таймауты или лимиты ключей
- Все 3 ключа (OLLAMA_API_KEY_1/2/3) — с той же проблемой
- Если Ollama не ответила — graceful degradation (null, отчёт пишет "агент не ответил")

### Fallback для GitHub
- Если GitHub Models не ответил — перекидываем на Mistral
- Fallback проверяет MISTRAL_API_KEY и MISTRAL_API_KEY_2

## HTML визуализация

- splash.html: https://zinadchdp.duckdns.org/research/deep_research_splash.html
- report.html: рядом с final_report.md в папке результата
- Доступно по: https://zinadchdp.duckdns.org/research/sandbox/deep_research/{folder}/report.html
- Caddy route: /research/* → /opt/zinaida/
