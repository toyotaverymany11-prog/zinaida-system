# Cascade Search — BrightData → DuckDuckGo → Server

## Паттерн каскадного поиска

Любой агент ищет по цепочке:
1. **BrightData SERP API** (Google результаты, 5000 запросов/мес бесплатно)
2. **DuckDuckGo** (бесплатно, без ключа)
3. **Server search** (локальные файлы /opt/zinaida/)

Каждый следующий источник — fallback, если предыдущий не сработал.

## Реализация в deep_research.py

Функция `cascade_search(query, max_results=5)`:
- Пробует `brightdata_search()` → Google через BrightData
- Если пусто — `ddgs_search()` → DuckDuckGo
- Если пусто — `server_search()` → rg по /opt/zinaida/

## Скрипт прямого вызова

```bash
# BrightData напрямую
python3 /opt/zinaida/scripts/web_search_brightdata.py "запрос" --limit 5

# DuckDuckGo напрямую (через deep_research.py)
python3 -c "import sys; sys.path.insert(0,'/opt/zinaida/scripts'); from deep_research import ddgs_search; import json; print(json.dumps(ddgs_search('запрос', 5), ensure_ascii=False, indent=2))"
```

## Лимиты

- BrightData: 5000 кредитов/мес (обновление 12 числа)
- DuckDuckGo: безлимит (но rate-limit может быть)
- Server: безлимит (локальный rg)
