# Провайдеры: httpx vs urllib — что когда использовать

**Создан:** 15.07.2026  
**Назначение:** Не тратить время на выбор — сразу знать какой HTTP-клиент нужен каждому провайдеру.

## Ключевое правило
Большинство LLM API принимают httpx без проблем. НО некоторые провайдеры **отклоняют запросы от httpx** и работают ТОЛЬКО через urllib.

| Провайдер | HTTP клиент | Почему |
|-----------|-------------|--------|
| Mistral | ✅ httpx (любой) | Стандартный OpenAI API |
| GitHub Models (Azure) | ✅ httpx (любой) | Стандартный Azure OpenAI |
| Ollama | ✅ httpx (любой) | OpenAI-совместимый |
| Zhipu | ❌ **только urllib** | httpx даёт 401 "токен истёк", хотя ключ живой |
| GigaChat | ❌ **только urllib + ssl._create_unverified_context()** | httpx даёт 429 rate limit даже с паузой 3с; SSL сертификат самоподписанный |
| OpenRouter | ✅ httpx | Стандартный OpenAI, но IP в РФ заблокирован |

## Почему urllib, а не httpx

### Zhipu (open.bigmodel.cn)
- `httpx.AsyncClient(verify=False)` → HTTP 401 "令牌已过期或验证不正确" (токен истёк)
- `urllib.request.urlopen()` → HTTP 200, нормальный ответ

**Причина:** Zhipu API проверяет заголовки и отклоняет нестандартные от httpx. urllib отправляет "чистые" заголовки.

### GigaChat (Сбер)
- `httpx.AsyncClient(verify=False)` → HTTP 429 или SSL error
- `urllib.request.urlopen(context=ssl._create_unverified_context())` → HTTP 200

**Причина:** Две проблемы:
1. **SSL:** GigaChat использует самоподписанный сертификат. `verify=False` в httpx не работает — падает с `CERTIFICATE_VERIFY_FAILED`. Нужен `ssl._create_unverified_context()`.
2. **Rate limit:** httpx отправляет больше concurrent запросов. Даже с `time.sleep(3)` между ними — httpx быстрее исчерпывает лимит (~1 req/3-5 сек).

## Шаблон для urllib-only провайдеров
```python
import urllib.request, json, ssl, time

ctx = ssl._create_unverified_context()  # для GigaChat

data = json.dumps({
    "model": "model-name",
    "messages": [{"role": "user", "content": "hi"}]
}).encode()

req = urllib.request.Request(
    "https://api.url.com/v1/chat/completions",
    data=data,
    headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json"
    },
    method="POST"
)

with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    result = json.loads(resp.read())

time.sleep(1)  # пауза между вызовами
```

## Шаблон для httpx-совместимых провайдеров
```python
import httpx

async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
    resp = await client.post(
        "https://api.url.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "model-name", "messages": [{"role": "user", "content": "hi"}]}
    )
    result = resp.json()
```

**Правило:** Если провайдер даёт 401/403/429 через httpx — попробовать через urllib. Если urllib даёт 200 — это провайдер, который НЕ ДРУЖИТ с httpx.
