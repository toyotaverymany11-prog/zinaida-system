# BrightData SERP API — Quick Reference

## Прямой curl (тестовый)
```bash
curl -s "https://api.brightdata.com/request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 929dbdc5-0160-4acd-9fe3-ca85d604a3fe" \
  -d '{"zone": "serp_api1", "url": "https://www.google.com/search?q=test&num=3&hl=ru", "format": "raw", "data_format": "html"}' | head -c 2000
```

## API
- **Endpoint:** `https://api.brightdata.com/request`
- **Auth:** `Authorization: Bearer <BRIGHTDATA_KEY>`
- **Zone:** `serp_api1`
- **Body:** `{"zone": "serp_api1", "url": "...", "format": "raw", "data_format": "html"}`
- **Ответ:** сырой HTML страницы поиска Google

## Прокси (альтернативный доступ)
```bash
curl --proxy brd.superproxy.io:33335 \
  --proxy-user brd-customer-hl_06b78e47-zone-serp_api1:ystzjjgy401n \
  -k "https://geo.brdtest.com/welcome.txt"
```

## Лимиты
- Бесплатный план: 5000 кредитов/мес
- 1 поиск = 1-10 кредитов (зависит от сложности)
- $5 добавлено на счёт при регистрации
- Ключ не протухает быстро (Олег получил и сразу работает)

## Где используется
- `/opt/zinaida/scripts/web_search_brightdata.py` — скрипт поиска
- `deep_research.py` — вызывает скрипт через subprocess
- `.env` — `BRIGHTDATA_KEY` в /root/.hermes/.env, /opt/zinaida/.env, /opt/zinaida/meta_agent/.env
