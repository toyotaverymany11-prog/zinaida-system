# Бесплатные поисковые API для агентов в РФ (актуально на 12.07.2026)

## Краткая сводка

| Сервис | Лимит | Работает в РФ | API ключ нужен | Годен? |
|--------|-------|---------------|----------------|--------|
| **Brave Search API** | $5 кредитов/мес (~1000 запросов) | ✅ | ✅ да | ✅ лучший |
| **SerpApi** | 100 кредитов/мес (~100 запросов) | ✅ | ✅ да | ✅ норм |
| **Google Custom Search** | 100 запросов/день | ✅ | ✅ ключ + cx ID | ✅ работает |
| **Mojeek** | 10000 запросов/мес | ✅ | ✅ | ⚠️ качество ниже |
| **DuckDuckGo (офиц. API)** | безлимит | ✅ | ❌ | ❌ только Instant Answers |
| **Bing Search** | 1000/мес | ✅ | ✅ | ⚠️ Azure нужен |
| **Tavily (dev)** | 432 error | ❌ | ✅ | ❌ лимит |
| **Qwant** | — | ❌ | ❌ | ❌ API закрыт 2023 |

## Google Custom Search — как получить ключ (3 шага)

### Шаг 1: Включить Custom Search API
1. Открыть https://console.cloud.google.com/apis/library
2. Найти **Custom Search API**
3. Нажать **Enable**

### Шаг 2: Создать API ключ
1. Открыть https://console.cloud.google.com/apis/credentials
2. Нажать **Создать учетные данные** → **API-ключ**
3. Если Google предлагает пробную версию ($300) — **проигнорировать**, не заполнять
4. Ключ появится в синем окошке: `AIzaSy...`

### Шаг 3: Создать поисковую систему (cx ID)
1. Открыть https://programmablesearchengine.google.com/
2. Нажать **Добавить** / **Создать**
3. В поле **«Сайты для поиска»** ввести `example.com` (обязательно! без сайта кнопка не активна)
4. Нажать **Создать**
5. После создания — зайти в **Настройки** → **Базовые**
6. Включить **«Поиск во всем интернете»** (эта опция становится активной только ПОСЛЕ создания с хотя бы одним сайтом)
7. Скопировать **Search Engine ID (cx)** — строка вида `929dbdc5-0160-4acd-9fe3-ca85d604a3fe`

### Проверка ключа
```python
import urllib.request, json
API_KEY = 'AIzaSy...'
CX = '929dbdc5-...'
url = f'https://customsearch.googleapis.com/customsearch/v1?key={API_KEY}&cx={CX}&q=test&num=1'
resp = urllib.request.urlopen(url, timeout=15)
data = json.loads(resp.read())
print('✅', data.get('searchInformation', {}).get('totalResults'))
```

## SerpApi — альтернатива (если Google не пошёл)

**Ссылка:** https://serpapi.com/  
**API эндпоинт:** `https://serpapi.com/search?q=ЗАПРОС&api_key=КЛЮЧ&engine=google&hl=ru`

**Бесплатный план:** 100 кредитов/мес.

**Как получить ключ:**
1. Открыть https://serpapi.com/
2. Зарегистрироваться (email)
3. Зайти в https://serpapi.com/manage-api-key
4. Скопировать ключ

**Проверка:**
```bash
curl -s "https://serpapi.com/search?q=test&api_key=ВАШ_КЛЮЧ&engine=google&num=3" | python3 -m json.tool
```

**Что нужно для web_search_proxy.py — заменить эндпоинт:**
```python
url = f'https://serpapi.com/search?q={urllib.parse.quote(query)}&api_key={API_KEY}&engine=google&hl=ru&num={num}'
```

## Brave Search API

**Ссылка:** https://brave.com/search/api/  
**API эндпоинт:** `https://api.search.brave.com/res/v1/web/search`

**Бесплатно:** $5 кредитов/мес (~1000 запросов).

**ВАЖНО:** Не путать `brave.com/search/api/` с `api.search.brave.com` — это разные вещи. Регистрация на сайте Brave.

## ПИТФОЛЛ: BrightData — НЕ поиск (12.07.2026)

Олег может скинуть ключ от **BrightData** (скрин с API формой, опции "Raw HTML", "Full JSON", "Markdown"). BrightData — это **аренда прокси для веб-скрапинга**, а не поисковый API. Он позволяет загрузить HTML страницы, но не искать по интернету. Если Олег говорит «ключ для поиска» и скидывает BrightData ключ — объяснить разницу и предложить SerpApi или Google Custom Search вместо него.

**Как отличить:**
- BrightData: ключ вида `92dbdc5-...` (UUID), форма с "Raw HTML / Full JSON / Markdown"
- Google: ключ вида `AIzaSy...` (начинается с AIza)
- SerpApi: ключ вида `...` (строка на дашборде)

## Как работает web_search в Hermes

Hermes использует **backend** для поиска, который настрачивается в `~/.hermes/config.yaml`:
```yaml
web:
  backend: tavily        # built-in: tavily, duckduckgo, google (не реализован)
  search_backend: tavily
  extract_backend: tavily
  api_key: "tvly-..."
```

При смене backend:
```bash
hermes config set web.backend duckduckgo
hermes config set web.search_backend duckduckgo
hermes config set web.extract_backend tavily  # extract остаётся на tavily
systemctl restart hermes-gateway
```

**DuckDuckGo** — работает без ключа, бесплатно. Единственная бесплатная built-in опция.

Если Tavily мёртв (432) — переключить на DuckDuckGo как временное решение.
