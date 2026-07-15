# Бесплатные поисковые API для AI агентов в РФ (2026)

**Дата:** 12.07.2026  
**Контекст:** Tavily dev-ключ дал 432 (лимит). Нужна бесплатная замена для `web_search` и `web_extract` в Hermes Agent.

## Поисковые API

### Brave Search API — 🥇 ЛУЧШАЯ ЗАМЕНА
- **2000 запросов/месяц** бесплатно
- Работает в РФ (не блокируется)
- Качество поиска: хорошее (близко к Google)
- Требует API-ключ: https://brave.com/search-api/
- `web_search` в Hermes можно переключить: `hermes config set web.backend brave`

### Mojeek API — для больших объёмов
- **10000 запросов/месяц** бесплатно
- Независимый поисковик (свой индекс, не зависит от Google/Bing)
- Качество индекса: ниже Google/Brave
- Требует API-ключ: https://mojeek.com/api

### Google Custom Search API
- **100 запросов/день** бесплатно
- Работает в РФ
- API-ключ: Google Cloud Console → Custom Search API
- Ограничение: ищет только по сайтам в вашей CSE (не весь интернет)

### Bing Search API
- **1000 запросов/месяц** бесплатно
- Требует Azure-подписку (нужна карта)
- Работает в РФ
- Полноценный поиск, хорошее качество

### DuckDuckGo (неофициально)
- Безлимитно, бесплатно
- Через библиотеку `ddgs` (pip install ddgs)
- Нарушает условия использования DuckDuckGo — риск блокировки
- `from ddgs import DDGS` — итератор результатов

## ❌ Не подходят
| Сервис | Причина |
|--------|---------|
| **Tavily (dev)** | 432 лимит, ключ не активирован |
| **Serper** | 50 запросов/месяц — ничтожно |
| **Qwant API** | Закрыт с 2023 |
| **Yandex.XML** | Требует договора, не AI-friendly |
| **Metafact** | Не поисковый API |

## Веб-экстракт (извлечение текста со страниц)

Поисковые API не умеют `web_extract`. Нужен отдельный инструмент:

### Jina AI Reader
- Бесплатно: 1000 запросов/мес
- Работает в РФ
- API: `GET https://r.jina.ai/<url>` — возвращает markdown
- Не требует ключа для базового использования

### Firecrawl
- Бесплатно: 500 страниц/мес
- Требует API-ключ
- Поддерживает JavaScript-рендеринг

### Собственный парсер
- `requests` + `BeautifulSoup` — бесплатно, безлимитно
- Нужен user-agent, обработка JS-контента не гарантируется

## Как настроить в Hermes

```bash
# 1. Brave Search как backend
hermes config set web.backend brave
hermes config set web.api_key "BRAVE_API_KEY"
systemctl restart hermes-gateway

# 2. DuckDuckGo как fallback (если Brave не настроен)
# Установка: pip install ddgs
# Переключение: hermes config set web.backend duckduckgo

# 3. Google Custom Search
hermes config set web.backend google
hermes config set web.api_key "GOOGLE_API_KEY"
hermes config set web.search_engine_id "CSE_ID"
```

## Текущий статус (12.07.2026)
- Tavily: 432 (лимит) — `web_search` не работает
- DuckDuckGo через ddgs: есть `pip install ddgs`, но не настроен как backend Hermes
- Hermes config: `web.backend: tavily` — без ключа, backend мёртв
- **Фикс:** `hermes config set web.backend duckduckgo` + `systemctl restart hermes-gateway`
