# Google Custom Search API — настройка (12.07.2026)

## Проблема

Tavily лёг (432 — лимит dev-ключа). Решили заменить веб-поиск для AI агента через Google Custom Search JSON API.

## Процесс

### 1. Получить API ключ
1. Открыть https://console.cloud.google.com/apis/credentials
2. Нажать «Создать учетные данные» → «API-ключ»
3. Ключ появляется сразу в синем окошке. Копировать.
4. (Опционально) Ограничить ключ по Custom Search API

### 2. Включить Custom Search API
1. Открыть https://console.cloud.google.com/apis/library
2. Найти **Custom Search API**
3. Нажать **Enable**

### 3. Получить Search Engine ID (cx) — ОБЯЗАТЕЛЬНО
Google требует **оба** параметра: `key` (API ключ) + `cx` (Search Engine ID).
Без cx — HTTP 400 «Request contains an invalid argument».

**Как получить cx:**
1. Открыть https://programmablesearchengine.google.com/
2. Нажать **«Создать»** / **«Add»**
3. В поле «Сайты для поиска» ввести `*` (звёздочка) — это означает «все сайты»
4. Нажать **«Создать»**
5. Скопировать **Search engine ID (cx)**

### 4. Проверка через curl
```bash
curl -s "https://customsearch.googleapis.com/customsearch/v1?key=AIza...&cx=017...fve&q=test"
```
Если приходит JSON с `items` — всё работает.

### 5. Ошибка: «проект не имеет доступа к Custom Search JSON API» (HTTP 403)
Причина: Custom Search API не включён в проекте. Фикс: https://console.cloud.google.com/apis/library → Enable.

### 6. Интеграция через Hermes config
```bash
hermes config set web.backend google
hermes config set web.search_backend google
hermes config set web.extract_backend google
hermes config set web.api_key "AIza..."
systemctl restart hermes-gateway
```
**Важно:** `hermes config set web.api_key` сохраняет ключ в config.yaml. Но Hermes встроенный web-клиент использует Tavily-клиент, а не Google напрямую. Google не built-in backend для Hermes (только Tavily и DuckDuckGo). Поэтому скрипт `/opt/zinaida/scripts/web_search_proxy.py` делает вызов напрямую через urllib.

### 7. Бесплатные лимиты
- Google Custom Search JSON API: **100 запросов/день** бесплатно
- После превышения: $5 за 1000 запросов

## Альтернативы (если Google не подошёл)

| Сервис | Бесплатно/мес | Качество | Ссылка |
|--------|--------------|----------|--------|
| **Brave Search API** | $5 кредитов = ~1000 запросов | Хорошее | https://brave.com/search/api/ |
| **Mojeek** | 10000 запросов | Ниже Google | https://mojeek.com/api |
| **Bing Search API** | 1000 запросов | Хорошее | Microsoft Azure |
| **Serper** | 50 запросов | Google через партнёра | https://serper.dev |
| **DuckDuckGo** | ❌ только Instant Answers | Нет полноценного API | — |

## Веб-экстракт (извлечение текста со страниц)

Поисковые API не умеют извлекать текст со страниц (content extraction). Для этого нужен отдельный инструмент:
- **Firecrawl** — платный
- **Jina AI Reader** — платный
- **Самописный парсер** — `web_search_proxy.py` содержит функцию `extract_url()`, которая парсит HTML через re.sub + html.unescape. Базовый, но бесплатный.
- **Hermes browser tools** — `browser_navigate` + `browser_snapshot(full=true)` + `web_extract` через Tavily (но Tavily лёг)

## Скрипт

`/opt/zinaida/scripts/web_search_proxy.py` — универсальный поисковый прокси:

```bash
# Поиск
python3 web_search_proxy.py "запрос" --limit 5

# Извлечение текста со страницы
python3 web_search_proxy.py --extract "https://example.com"
```

Ключ читается из `/root/.hermes/.env` (GOOGLE_API_KEY=...) или из config.yaml.
