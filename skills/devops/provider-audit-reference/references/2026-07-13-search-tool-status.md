# Статус поисковых инструментов (13.07.2026)

## Tavily
- **Статус:** ❌ 432 — лимит 1000 запросов/мес исчерпан на 13.07.2026
- **Затрагивает:** `web_search()`, `web_extract()`, `deep_research.py` (3 из 4 агентов)
- **Решение:** DuckDuckGo через Python `from ddgs import DDGS`

## DuckDuckGo (работает)
- **Статус:** ✅ работает, бесплатно, безлимит
- **Использование:**
```python
from ddgs import DDGS
results = list(DDGS().text('запрос', max_results=5))
for r in results:
    print(r['title'], r['href'])
```
- **Установка:** `pip install ddgs` (уже установлен)
- **Импорт:** `from ddgs import DDGS` — НЕ `DuckDuckGoSearch`!

## Browser (Hermes built-in)
- **Статус:** ✅ работает
- **Инструменты:** `browser_navigate(url)`, `browser_click()`, `browser_snapshot()`, `browser_scroll()`
- **Лимиты:** безлимит (через локальный или cloud браузер)
- **Использовать для:** чтения документации, GitHub, сайтов, куда не пускает Tavily

## GitHub API
- **Статус:** ✅ работает через browser_navigate
- **Альтернатива:** curl через `api.github.com` с токеном
