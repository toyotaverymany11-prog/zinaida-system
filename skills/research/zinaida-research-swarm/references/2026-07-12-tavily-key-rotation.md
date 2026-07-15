# Tavili поиск — работа с ключами и fallback

## Где хранится ключ
`/opt/zinaida/sandbox/configs/api_keys.json` → ключ `tavily`

## Как проверить
```bash
curl -s -w "\nHTTP:%{http_code}\n" -m 15 "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"тест","api_key":"<KEY>","max_results":1}'
```

200 = работает. 432 = превышен лимит dev-плана. Нужен новый ключ.

## Процедура обновления ключа
1. Олег даёт новый ключ (chat или screenshot)
2. Апдейт в api_keys.json:
   ```python
   import json
   data = json.load(open('/opt/zinaida/sandbox/configs/api_keys.json'))
   data['tavily'] = '<новый ключ>'
   json.dump(data, open('/opt/zinaida/sandbox/configs/api_keys.json','w'), indent=4)
   ```
3. Проверить curl-ом

## DuckDuckGo fallback
`/opt/zinaida/meta_agent/web_tools.py` — search_web() сначала пробует DuckDuckGo (бесплатно, без ключа), потом Tavily.
Порядок переключён 12.07.2026: DDGS теперь первый, Tavily — второй.

## Tavily для extract (web_extract)
Tavily extract использует тот же ключ. Если Tavily лимит — extract тоже не работает. Только браузер или curl.
