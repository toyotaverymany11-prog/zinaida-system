---
name: tavily-search
description: "Веб-поиск через Tavily API. Использовать когда web_search не работает."
version: 1.0.0
author: Zinaida-System
---

# Tavily Search — веб-поиск через Tavily API

## Когда использовать
- Когда `web_search` возвращает ошибку (403, авторизация)
- Когда нужен поиск по интернету в любом профиле (default, lera, agent2)
- Для поиска референсов, новостей, информации по теме поста

## Статус
- **Подключён системно** — ключ в `/root/.hermes/.env` (TAVILY_API_KEY)
- **backend прописан** в корневом config.yaml: `web.backend: tavily`
- **Лимит:** 1000 запросов/месяц бесплатно
- **web_search работает** после перезапуска сессии Hermes

## Как использовать напрямую (fallback)
Tavily API ключ лежит в `/root/.hermes/.env` (TAVILY_API_KEY).
Для поиска используй curl:

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'"$TAVILY_API_KEY"'", "query": "твой запрос", "max_results": 5}' | python3 -m json.tool
```

Или через Python (полезно когда нужно обработать результат):
```python
import requests, json, os

api_key = os.environ.get("TAVILY_API_KEY", "")
# или читай из файла: open("/root/.hermes/.env").read()
resp = requests.post("https://api.tavily.com/search", json={
    "api_key": api_key,
    "query": "твой запрос",
    "max_results": 5
})
data = resp.json()
for r in data.get("results", []):
    print(f"{r['title']}: {r['url']}")
```

## Параметры
- `query` (обязательно) — поисковый запрос
- `max_results` — от 1 до 10 (по умолчанию 5)
- `search_depth` — "basic" (быстро) или "advanced" (глубоко, больше токенов)

## Бесплатный лимит
1000 запросов в месяц. Не трать на ерунду.

## ЗАТЫК: `***` — маскировка, НЕ подстановка
`***` в командах Hermes — это маскировка ВЫВОДА, а не подстановка секрета.
- В `echo "export KEY=***"` в файл запишется буквально `***`
- В `subprocess.run` внутри execute_code `***` тоже не подставится
- Работает ТОЛЬКО в прямых terminal() вызовах с `Authorization: Bearer ***`
- Если нужно сохранить ключ в файл — пиши ПОЛНЫЙ ключ (Hermes замаскирует вывод, но в файл запишется верно)

## Референсы
- `references/hermes-tavily-setup.md` — настройка Tavily в Hermes config.yaml, документация
