# GigaChat — полный протокол тестирования и работа с rate limit

**Дата:** 11.07.2026  
**Статус:** ✅ Работает, модель GigaChat:2.0.28.2  

## Результаты тестирования

| Шаг | Результат | Время |
|-----|-----------|-------|
| OAuth2 (получение токена) | ✅ HTTP 200, токен получен | ~1 сек |
| Chat completion (первый) | ✅ HTTP 200, ответ есть | ~5 сек |
| Chat completion (второй, без паузы) | ❌ HTTP 429 Too Many Requests | - |

## Rate limit

GigaChat имеет rate limit ~1 запрос в 3-5 секунд. Это НЕ ошибка аутентификации — токен валиден, но сервер не принимает частые запросы.

**Симптомы 429:**
```json
{"status":429,"message":"Too Many Requests"}
```

**Фикс:**
```python
import time
time.sleep(3)  # ← пауза перед каждым запросом
```

**⚠️ httpx НЕ РАБОТАЕТ с GigaChat**
httpx.AsyncClient(verify=False) даёт 429 даже с паузой. Правильный способ — `urllib.request` + `ssl._create_unverified_context()`:
```python
import urllib.request, ssl
ctx = ssl._create_unverified_context()
req = urllib.request.Request(url, data=..., headers=..., method="POST")
with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
    result = json.loads(resp.read())
```

Если делать несколько параллельных запросов (ThreadPoolExecutor в QA-оркестраторе), только ОДИН пройдёт — остальные 429. Для параллельной работы нужно последовательно с паузой.

## OAuth2 — точный алгоритм

1. POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth
   - Header: `Authorization: Basic {base64(client_id:client_secret)}`
   - Header: `Content-Type: application/x-www-form-urlencoded`
   - Header: `RqUID: {uuid}`
   - Body: `scope=GIGACHAT_API_PERS`
   - SSL: самоподписанный → `ssl._create_unverified_context()`

2. POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions
   - Header: `Authorization: Bearer {access_token}`
   - Header: `Content-Type: application/json`
   - Тело: OpenAI-совместимый JSON
   - SSL: самоподписанный → `ssl._create_unverified_context()`

## RqUID

Это UUIDv4, который GigaChat использует для отслеживания запросов. Должен быть уникальным для каждого OAuth-запроса.
Используемый: `019d967c-5279-7677-bd29-e4e26eb88431`

## Скрипт проверки

```bash
python3 /opt/zinaida/sandbox/test_gigachat.py
```
