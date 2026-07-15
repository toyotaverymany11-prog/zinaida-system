---
name: provider-master-trigger
description: "УНИВЕРСАЛЬНЫЙ ТРИГГЕР: при любом упоминании любого LLM провайдера — загружает этот навык, который показывает сводку и ссылки на детальные инструкции. Решает проблему 'забыла про специфику провайдера'."
version: 2.0.0
author: Zinaida
license: MIT
metadata:
  hermes:
    triggers:
      - ollama
      - gigachat
      - mistral
      - deepseek
      - openrouter
      - github
      - zhipu
      - groq
      - cerebras
      - siliconflow
      - cohere
      - провайдер
      - provider
      - api ключ
      - ключ
      - бесплатный
      - бесплатно
      - free model
      - нейросеть
      - модель
      - llm
      - баланс
      - лимит
      - rate limit
      - 429
      - 402
      - 401
    tags: [провайдеры, api, ключи, память, триггер, боевой]
    related_skills:
      - devops/provider-audit-reference
      - devops/gigachat-integration
      - devops/memory-first-protocol
      - devops/zinaida-tech-protocol
---
# 🚨 ПРОВАЙДЕРЫ: ПОЛНАЯ СВОДКА (обновлено 15.07.2026)

**Главное правило:** Никогда не говори "провайдер мёртв" или "не работает" не проверив по этой инструкции.

## 8002 — СТРАХОВОЧНЫЙ РОУТЕР (полностью бесплатный, независим от DeepSeek)
ORDER_CHAT = ["ollama", "mistral", "github", "zhipu", "gigachat"]
Порт: 8002. Файл: /opt/zinaida/meta_agent/zinaida_openai_proxy.py

## ТАБЛИЦА ВСЕХ ПРОВАЙДЕРОВ

| Провайдер | Статус | Бесплатно | Способ вызова | Ключи |
|-----------|--------|-----------|--------------|-------|
| **Ollama** | ✅ Работает | ✅ Да | Bearer, OpenAI-совместимый | 3 ключа: Zina (2), Григорий (1) |
| **Mistral** | ✅ Работает | ✅ Да (~1B токенов/мес) | Bearer, OpenAI | 3 ключа: Zina, Zina2, Григорий |
| **GitHub Models** | ✅ Работает | ✅ Да (15 RPM) | Bearer, Azure endpoint | 2 токена: Zina, Григорий |
| **Zhipu (智谱)** | ✅ Работает | ✅ Да (GLM-4-Flash) | Bearer, OpenAI | 1 ключ |
| **GigaChat** | ✅ Работает | ✅ Да (1M токенов/мес) | **OAuth2, urllib, SSL bypass, пауза 3с** | 1 ключ base64 |
| **DeepSeek** | ✅ Работает | ❌ Платный | Bearer, OpenAI | 3 ключа ($ баланс) |
| **OpenRouter** | ❌ Блокировка | ✅ Модели бесплатно | **IP РФ заблокирован (403)** | 2 ключа |
| **Groq** | ❌ Не проверен | ✅ Да (30 RPM) | Bearer, OpenAI | 2 ключа |
| **Cerebras** | ❌ Не проверен | ✅ Да (1M токенов/день) | Bearer, OpenAI | 1 ключ |
| **SiliconFlow** | ❌ Не проверен | ✅ Да ($14 кредитов) | Bearer, OpenAI | 1 ключ |

## СПЕЦИФИКА КАЖДОГО (коротко, чтобы не гадать)

### Ollama
- **URL:** https://ollama.com/v1
- **Модель:** gemma4:31b (единственная бесплатная, gemma3:4b retired 15.07)
- **Bearer токен** целиком, с точкой
- **GET /v1/models** — список моделей. Бесплатные отвечают, Pro дают 403
- **Симптом "не работает":** 410 = retired модель, 403 = Pro, пустой ответ = бесплатный тариф не даёт вывод

### GigaChat (Сбер) — НЕЛЬЗЯ через httpx
- **OAuth2 двухшаговый:** сначала получить access_token, потом с ним чат
- **Только urllib.request + ssl._create_unverified_context()**
- **Пауза 3 секунды** между получением токена и чатом (429 иначе)
- **Ключ:** base64(client_id:client_secret)
- **Симптом "не работает":** 401 = токен протух (30 мин) → получить новый. SSL = verify=False не помогает, нужен _create_unverified_context. 400 = ключ неправильно кодируется

### Mistral
- **URL:** https://api.mistral.ai/v1
- **Модель:** mistral-small-latest (бесплатная)
- 3 ключа работают. Rate limit ~1 req/сек на ключ

### GitHub Models
- **URL:** https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21
- **Модель:** gpt-4o-mini (бесплатно)
- **429 rate limit** — нормально, провайдер ЖИВ. Подождать 60 сек восстановится
- 2 токена

### Zhipu
- **URL:** https://open.bigmodel.cn/api/paas/v4
- **Модель:** glm-4-flash (бесплатно)
- Bearer токен, OpenAI-совместимый

## ЧТО ДЕЛАТЬ ЕСЛИ ПРОВАЙДЕР "НЕ РАБОТАЕТ"
1. Загрузить этот навык
2. Посмотреть в таблицу — какая специфика
3. Проверить прямым вызовом по шаблону из таблицы
4. Только потом говорить результат

## ССЫЛКИ
- Навык provider-audit-reference — полный справочник с датами лимитов
- Навык gigachat-integration — полная инструкция по GigaChat с кодом
- Файл: /opt/zinaida/meta_agent/zinaida_openai_proxy.py — код 8002 роутера
