# Tavily в Hermes: настройка и конфигурация

## Как подключить
1. Получить ключ: https://app.tavily.com
2. Добавить в `.env`:
   ```
   TAVILY_API_KEY=tvly-...
   ```
3. В `config.yaml`:
   ```yaml
   web:
     backend: tavily
     # или раздельно:
     search_backend: tavily
     extract_backend: tavily
   ```
4. Авто-детект: Hermes сам подхватит если `TAVILY_API_KEY` есть в окружении.
5. Перезапустить сессию Hermes или gateway.

## Бесплатный лимит
1000 запросов/месяц.

## Fallback если web_search не работает
Использовать curl напрямую:
```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'"$TAVILY_API_KEY"'", "query": "запрос", "max_results": 3}'
```

## Tavily в профилях
- Если ключ в корневом `.env` — доступен всем профилям
- Если нужно только для конкретного профиля — положи ключ в `.env` профиля

## Документация Hermes
Источник: https://hermes-agent.nousresearch.com/docs/features/media-and-web/web-search
В документации описаны все бэкенды: Firecrawl, SearXNG, Brave, DDGS, Tavily, Exa, Parallel, xAI.
