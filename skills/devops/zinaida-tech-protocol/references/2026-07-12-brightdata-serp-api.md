# BrightData SERP API — ссылки и инструкция

**Дата:** 12.07.2026  
**Источник:** Олег дал ссылку https://brightdata.com/cp/web_access/new?type_selected=1  
**Docs:** https://docs.brightdata.com/scraping-automation/serp-api/introduction  
**Quick Start:** https://docs.brightdata.com/scraping-automation/serp-api/quickstart  
**Auth (API Reference):** https://docs.brightdata.com/api-reference/authentication  
**Create API:** https://brightdata.com/cp/web_access/new?type_selected=1

## Как работает
BrightData SERP API — прокси для запросов к поисковым системам (Google, Bing и др.). Отправляет запрос через свои прокси, обходит блокировки.

## Аутентификация
- **Bearer** токен в заголовке: `Authorization: Bearer <API_KEY>`
- Ключ берётся из дашборда BrightData (Settings → API Keys)
- Ключ `929dbdc5-0160-4acd-9fe3-ca85d604a3fe` (от Олега) — вероятно zone/access ID, не Bearer токен
- Настоящий токен нужно скопировать из **Settings → API Keys** в дашборде BrightData

## Пример curl
```bash
curl -X POST "https://api.brightdata.com/request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ВАШ_ТОКЕН>" \
  -d '{
    "zone": "serp_api1",
    "url": "https://www.google.com/search?q=Hermes+Agent&hl=ru",
    "format": "raw",
    "data_format": "html"
  }'
```

## Python скрипт
`/opt/zinaida/scripts/web_search_brightdata.py`

Использование:
```bash
python3 /opt/zinaida/scripts/web_search_brightdata.py "запрос" --limit 5
python3 /opt/zinaida/scripts/web_search_brightdata.py --extract "https://example.com"
```

Читает ключ из `.env` (`BRIGHTDATA_API_KEY`) или из аргумента `--key`.

## Ограничение
- Возвращает **HTML** страницы Google, не JSON
- Нужно парсить результат (регулярки, BeautifulSoup)
- Google меняет HTML — парсинг может ломаться
- API платный (сколько стоит — не проверено)
