---
name: gigachat-integration
description: "Полная инструкция по GigaChat: OAuth2 аутентификация, ключи, API вызовы, интеграция в роутер и Hermes Studio. Использовать при любых упоминаниях GigaChat."
version: 1.0.0
author: Zinaida
metadata:
  hermes:
    tags: [gigachat, sber, oauth2, провайдер, api]
    related_skills: [devops/provider-audit-reference]
---

# GigaChat — Полная интеграция

## 1. ОТЛИЧИЕ ОТ ДРУГИХ ПРОВАЙДЕРОВ

**КРИТИЧЕСКИ ВАЖНО:** GigaChat НЕ использует Bearer токен как Mistral/GitHub/Ollama.
У него ДВУХШАГОВАЯ аутентификация через OAuth2:

1. **Шаг 1 — OAuth2:** Получить access_token по client_id:client_secret
2. **Шаг 2 — Chat:** Использовать access_token как Bearer (живёт ~30 минут)

**Ключ — это base64(client_id:client_secret).** Не Bearer токен, не API-ключ.
Если скопировать ключ и просто подставить в Authorization: Bearer — будет 401/ошибка.

## 2. КЛЮЧИ

```yaml
# Основной ключ (base64 client_id:client_secret):
GigachatAPI: MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==

# Отдельно (на всякий случай):
GIGACHAT_CLIENT_ID: 019d967c-5279-7677-bd29-e4e26eb88431
GIGACHAT_CLIENT_SECRET: c4cdf7a0-c433-40a8-8295-3335d0376209
```

Хранятся в:
- `/opt/zinaida/.env`
- `/opt/zinaida/meta_agent/.env`
- `/opt/zinaida/design/sysadmin/SECRETS.md`

## 3. ТОЧНЫЕ КОМАНДЫ

### 3.1 Получить access_token

```python
import urllib.request, json, ssl

ssl_ctx = ssl._create_unverified_context()  # GigaChat использует самоподписанный сертификат!

GIGA_KEY = "MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ=="

auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
headers = {
    "Authorization": f"Basic {GIGA_KEY}",
    "Content-Type": "application/x-www-form-urlencoded",
    "RqUID": "019d967c-5279-7677-bd29-e4e26eb88431",
}
data = "scope=GIGACHAT_API_PERS"

req = urllib.request.Request(auth_url, data=data.encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
    body = json.loads(resp.read())
    access_token = body["access_token"]  # ← вот этот токен для Bearer
```

### 3.2 Chat completion

```python
chat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
chat_data = json.dumps({
    "model": "GigaChat",  # НЕ GigaChat:latest — без :latest!
    "messages": [{"role": "user", "content": "текст"}],
    "max_tokens": 1000
}).encode()
chat_headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
req = urllib.request.Request(chat_url, data=chat_data, headers=chat_headers, method="POST")
with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
    result = json.loads(resp.read())
    print(result["choices"][0]["message"]["content"])
```

### 3.3 curl для быстрой проверки

```bash
# Шаг 1: получить токен
TOKEN=$(curl -s -k -X POST "https://ngw.devices.sberbank.ru:9443/api/v2/oauth" \
  -H "Authorization: Basic MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "RqUID: 019d967c-5279-7677-bd29-e4e26eb88431" \
  -d "scope=GIGACHAT_API_PERS" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Шаг 2: отправить запрос
curl -s -k -X POST "https://gigachat.devices.sberbank.ru/api/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"GigaChat","messages":[{"role":"user","content":"say hi"}],"max_tokens":20}'
```

## 4. ВАЖНЫЕ ОСОБЕННОСТИ

| Особенность | Деталь |
|-------------|--------|
| SSL ошибка | Самоподписанный сертификат | `ssl._create_unverified_context()` |
| **402 Payment Required** | **Ежемесячный лимит 1M токенов исчерпан** | **Ждать обновления лимита (~10-11 числа каждого месяца). Проверить после ~10.08.2026. См. ссылку `references/2026-07-12-provider-limits-reset-dates.md` в skills/devops/provider-audit-reference/.** |
| **Токен живёт** | ~30 минут. Нужно обновлять перед каждым запросом или кешировать |
| **Лимиты** | Бесплатно до 1M токенов/месяц |
| **Rate limit** | **429 Too Many Requests** — ~1 запрос в 3-5 секунд. ОБЯЗАТЕЛЬНО `time.sleep(3)` перед каждым chat-запросом |
| **Модели** | GigaChat:latest, GigaChat:2.0.28.2 |
| **Русский** | Отличный русский, лучше многих западных моделей |
| **Скорость** | ~5-10 сек на ответ |
| **chat_url (с портом)** | https://gigachat.devices.sberbank.ru/api/v1/chat/completions |
| **auth_url (с портом)** | https://ngw.devices.sberbank.ru:9443/api/v2/oauth |

## 5. RATE LIMIT И HTTPX — КРИТИЧЕСКИ ВАЖНО (обновлено 11.07.2026)

GigaChat имеет жёсткий rate limit. Без паузы между запросами получаешь 429.

**⚠️ GIGACHAT НЕ РАБОТАЕТ ЧЕРЕЗ HTTPX! (открытие 11.07.2026)**

`httpx.AsyncClient(verify=False)` с GigaChat даёт **429** даже с паузой 3 сек. GigaChat не любит httpx-соединения с самоподписанным сертификатом. Единственный рабочий способ — `urllib.request` + `ssl._create_unverified_context()`.

```python
# ❌ НЕ РАБОТАЕТ — httpx даёт 429
async with httpx.AsyncClient(verify=False) as c:
    resp = await c.post(GIGA_CHAT_URL, headers=...)

# ✅ РАБОТАЕТ — urllib + ssl_ctx
import urllib.request, ssl
ssl_ctx = ssl._create_unverified_context()
req = urllib.request.Request(chat_url, data=data, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
    result = json.loads(resp.read())
```

**АСИНХРОННЫЙ шаблон для роутера (FastAPI):**
```python
import urllib.request as _urllib, ssl as _ssl, time, asyncio
_giga_ssl_ctx = _ssl._create_unverified_context()
_giga_last_request = 0.0

async def _call_gigachat(prompt: str, token: str) -> str:
    global _giga_last_request
    # Пауза 3 сек между запросами (rate limit!)
    now = time.time()
    since_last = now - _giga_last_request
    if since_last < 3.0:
        await asyncio.sleep(3.0 - since_last)
    
    data = json.dumps({"model": "GigaChat:latest", "messages": [
        {"role": "user", "content": prompt}
    ], "max_tokens": 2048, "temperature": 0.3}).encode()
    
    req = _urllib.Request(GIGA_CHAT_URL, data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST")
    with _urllib.urlopen(req, context=_giga_ssl_ctx, timeout=30) as resp:
        result = json.loads(resp.read())
        _giga_last_request = time.time()
        return result["choices"][0]["message"]["content"]
```

**ТРИ ГЛАВНЫХ ГРАБЛИ (проверено на практике 11.07.2026):**

| Проблема | Почему | Фикс |
|----------|--------|------|
| `SSL: CERTIFICATE_VERIFY_FAILED` | У GigaChat самоподписанный сертификат | `ssl._create_unverified_context()` |
| `HTTP 429 Too Many Requests` | Лимит запросов — ~1 запрос в 3-5 сек | `time.sleep(3)` перед каждым запросом |
| `401 Unauthorized` через 30 минут | Токен живёт ~30 мин, потом протухает | Получить новый токен через OAuth2 |

**⚠️ GIGACHAT НЕ РАБОТАЕТ ЧЕРЕЗ HTTPX! (открытие 11.07.2026)**

`httpx.AsyncClient(verify=False)` с GigaChat даёт **429** даже с паузой. GigaChat не любит httpx-соединения с самоподписанным сертификатом. Единственный рабочий способ — `urllib.request` + `ssl._create_unverified_context()`.

```python
# ❌ НЕ РАБОТАЕТ — httpx даёт 429
async with httpx.AsyncClient(verify=False) as c:
    resp = await c.post(GIGA_CHAT_URL, headers=...)

# ✅ РАБОТАЕТ — urllib + ssl_ctx
import urllib.request, ssl
ssl_ctx = ssl._create_unverified_context()
req = urllib.request.Request(chat_url, data=data, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
    result = json.loads(resp.read())
```

**Правильный синхронный шаблон с паузой:**
```python
import time, urllib.request, json, ssl
ssl_ctx = ssl._create_unverified_context()

# Получить токен
token = get_giga_token()

# 🟢 Пауза перед каждым запросом — ОБЯЗАТЕЛЬНО
time.sleep(3)

# Отправить запрос
data = json.dumps({"model":"GigaChat","messages":[{"role":"user","content":"Привет"}],
req = urllib.request.Request(chat_url, data=chat_data,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST")
with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
    result = json.loads(resp.read())
```

**Правильный АСИНХРОННЫЙ шаблон (для роутера):**
```python
import urllib.request as _urllib, json, ssl as _ssl
_giga_ssl_ctx = _ssl._create_unverified_context()
_giga_last_request = 0.0

async def _call_gigachat(prompt: str, token: str) -> str:
    global _giga_last_request
    # Пауза 3 сек между запросами (rate limit!)
    now = time.time()
    since_last = now - _giga_last_request
    if since_last < 3.0:
        await asyncio.sleep(3.0 - since_last)
    
    data = json.dumps({"model": "GigaChat:latest", "messages": [
        {"role": "user", "content": prompt}
    ], "max_tokens": 2048, "temperature": 0.3}).encode()
    
    req = _urllib.Request(GIGA_CHAT_URL, data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST")
    with _urllib.urlopen(req, context=_giga_ssl_ctx, timeout=30) as resp:
        result = json.loads(resp.read())
        _giga_last_request = time.time()
        return result["choices"][0]["message"]["content"]
```

**Если всё равно 429:**
- Увеличить паузу до 5-10 секунд
- Проверить что не отправилось несколько параллельных запросов
- GigaChat имеет общий лимит на аккаунт, не только на ключ

## 5. ИНТЕГРАЦИЯ В РОУТЕР (Zinaida-Router, порт 8002)

Роутер (`zinaida_openai_proxy.py`) уже умеет работать с GigaChat, но ключ нужно правильно передавать:

1. Добавить в .env: `GIGACHAT_AUTH_KEY=MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==`
2. В роутере: перед запросом к GigaChat — вызвать OAuth2, получить токен, подставить в Bearer
3. Проверить что `_gigachat_clean_messages` не падает (известный баг с list content — исправлен)

## 6. ДОБАВЛЕНИЕ В HERMES STUDIO

Через прямой API вызов (OAuth2 не поддерживается MCP провайдерами стандартно):
- Лучше добавить GigaChat в роутер 8002/8003 как fallback
- Либо создать custom provider с предварительно полученным Bearer токеном

## 7. ПРОВЕРКА РАБОТОСПОСОБНОСТИ

```bash
python3 /opt/zinaida/sandbox/test_gigachat.py
```
Должен вывести:
```
✅ Токен получен
✅ HTTP 200
```

## 8. ЧАСТЫЕ ОШИБКИ

| Ошибка | Причина | Решение |
|--------|---------|---------|
| SSL CERTIFICATE_VERIFY_FAILED | Самоподписанный сертификат | Использовать `ssl._create_unverified_context()` |
| 401 в chat | Токен протух (живёт ~30 мин) | Получить новый access_token через OAuth2 |
| 400 BAD_REQUEST | Неверный RqUID | Использовать `019d967c-5279-7677-bd29-e4e26eb88431` |
| 401 при OAuth2 | Неверный base64 ключ | Проверить что client_id:client_secret правильно закодированы |
