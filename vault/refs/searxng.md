# SearXNG — бесплатный мета-поиск

## Дата установки: 18.07.2026
## Статус: ✅ РАБОТАЕТ

## Адрес
http://localhost:8888

## Движки
Google, Bing, DuckDuckGo, Wikipedia, Qwant

## Установка
Docker-compose в /opt/zinaida/searxng/docker-compose.yml

## Команда
```bash
curl -s "http://localhost:8888/search?q=запрос&format=json&limit=5"
```

## Параметры
- categories=news — новости
- categories=science — наука
- limit=10 — больше результатов

## Важно
- Восстанавливается через `docker compose -f /opt/zinaida/searxng/docker-compose.yml up -d`
- Не требует ключа
- 0 токенов
