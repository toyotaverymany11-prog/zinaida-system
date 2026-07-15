# 8002 Роутер (Zinaida-Router v4.0): полная диагностика

**Дата:** 12.07.2026  
**Файл:** `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`  
**Порт:** 8002  
**Systemd:** `zinaida-router.service`

## ⚠️ КРИТИЧЕСКИЕ ПРОБЛЕМЫ (STATE 12.07.2026)

### 1. .env файл не содержит API-ключи OpenRouter, GitHub, Zhipu

Роутер грузит переменные из `/opt/zinaida/.env` (строка 44-55):

```python
ENV_PATH = Path("/opt/zinaida/.env")
```

НО ключи для OpenRouter, GitHub и Zhipu лежат в `/opt/zinaida/meta_agent/.env`.

**Статус провайдеров из /status:**
| Провайдер | Ключей | Статус |
|-----------|--------|--------|
| openrouter | 0 | ❌ не добавлен в цепочку |
| github | 0 | ❌ ключ в meta_agent/.env |
| zhipu | 0 | ❌ ключ в meta_agent/.env |
| mistral | 2 | ✅ жив (2178 ok) |
| deepseek_flash | 1 | ✅ жив (3318 ok) — ПЛАТНЫЙ |
| gigachat | 1 | 💀 мёртв (2517 ошибок 402) |

### 2. OpenRouter настроен, но НЕ В ЦЕПОЧКЕ FALLBACK

Провайдер `openrouter` описан в PROVIDERS (строка 89-96):
```python
"openrouter": {
    "model": "google/gemini-2.0-flash-exp:free",
    "paid": False,
    ...
}
```

НО не добавлен ни в одну из ORDER-цепочек (строки 149-151):
```python
ORDER_CHAT = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]
ORDER_CODE = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]
ORDER_CREATIVE = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]
```

Заголовок файла: "Gemini-First + DeepSeek Fallback" — НО Gemini (OpenRouter) не вызывается вообще.

### 3. GigaChat мёртв (402) но стоит вторым в цепочке

Статус из /status: `gigachat: fail_count=2517, last_error="health HTTP 402"`

Каждый запрос пытается GigaChat → ждёт таймаут → падает → только потом следующие. GigaChat не работает (нет средств на аккаунте), а стоит **вторым** в цепочке.

### 4. Реальная рабочая цепочка

Из-за проблем выше реальная цепочка выглядит так:

```
Mistral (✅ работает) → GigaChat (💀 402, waste of time) → GitHub (0 keys) → Zhipu (0 keys) → DeepSeek Flash (✅ платный, но работает)
```

Все запросы, которые Mistral не может обработать, падают до DeepSeek Flash (платный), потому что 3 из 5 провайдеров перед ним не работают.

## КАК ДОЛЖНО БЫТЬ

### Шаг 1: Слить .env
Добавить в `/opt/zinaida/.env`:
- OPENROUTER_KEY из `/opt/zinaida/meta_agent/.env`
- GITHUB_TOKEN из `/root/.hermes/.env`
- ZHIPU_API_KEY из `/opt/zinaida/meta_agent/.env`

### Шаг 2: Починить цепочку

```python
# ПРАВИЛЬНАЯ цепочка: все бесплатные первыми, GigaChat выкинуть
ORDER_CHAT = ["openrouter", "github", "mistral", "zhipu", "deepseek_flash"]
ORDER_CODE = ["openrouter", "github", "mistral", "zhipu", "deepseek_flash"]
ORDER_CREATIVE = ["openrouter", "github", "mistral", "zhipu", "deepseek_flash", "deepseek_pro"]
```

Логика порядка:
1. **openrouter** — Gemini 2.0 Flash Free — лучшая бесплатная модель, конкурирует с GPT-4o mini
2. **github** — gpt-4.1-mini — бесплатно через GitHub токен
3. **mistral** — mistral-large-latest — 2 ключа, 2000+ успешных запросов
4. **zhipu** — glm-4-flash — бесплатно, русский тянет
5. **deepseek_flash** — платный, копеечный ($0.27/M) — последняя инстанция
6. **deepseek_pro** — только для CREATIVE (генерация постов/контента) — $1.42/M

### Шаг 3: GigaChat убрать из цепочки (выключить, пока не появится баланс)

## ТЕСТ ПОСЛЕ ИЗМЕНЕНИЙ

```bash
# Проверка здоровья
curl -s http://127.0.0.1:8002/status | python3 -m json.tool

# Все бесплатные должны быть:
# - available: true
# - keys > 0
# - paid: false
# - alive: true
```

## СВЯЗАННЫЕ ФАЙЛЫ

| Файл | Описание |
|------|----------|
| `/opt/zinaida/meta_agent/zinaida_openai_proxy.py` | Сам роутер (960 строк, FastAPI, порт 8002) |
| `/opt/zinaida/.env` | .env файл роутера (не хватает ключей) |
| `/opt/zinaida/meta_agent/.env` | .env файл с ключами OpenRouter, Zhipu |
| `/root/.hermes/.env` | .env файл с GITHUB_TOKEN |
| `/opt/zinaida/shared_memory/cost_log.json` | Лог стоимости (всего $0.0018 когда-либо) |
