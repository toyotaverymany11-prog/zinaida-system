---
name: provider-master-trigger
description: "УНИВЕРСАЛЬНЫЙ ТРИГГЕР: при любом упоминании LLM провайдера или HTTP ошибке. Гарантия: либо работает, либо доклад Олегу с полным контекстом."
version: 3.0.0
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
      - модель
      - llm
      - rate limit
      - 429
      - 402
      - 401
      - 403
      - 410
      - 500
      - SSL
      - CERTIFICATE_VERIFY_FAILED
      - timeout
      - dead
      - мёртв
      - не работает
      - retired
      - не получается
      - ошибка
      - сломалось
    tags: [провайдеры, api, ключи, память, триггер]
    related_skills:
      - devops/provider-audit-reference
      - devops/gigachat-integration
      - devops/memory-first-protocol
---
# 🚨 ЖЕЛЕЗНОЕ ПРАВИЛО: ГАРАНТИЯ РАБОТЫ ПРОВАЙДЕРОВ

**Если что-то не работает — я не останавливаюсь на первой ошибке.**
Я иду по цепочке пока либо не заработает, либо не смогу сама.

## АЛГОРИТМ (обязателен при любой проблеме)
1. Загрузить этот навык
2. Посмотреть в таблицу "Ошибка → что делать"
3. Сделать то что написано
4. Не помогло? Найти другую бесплатную модель (список через API провайдера)
5. Не помогло? Попробовать другой способ вызова (urllib вместо httpx и т.д.)
6. Не помогло? Доложить Олегу: что пробовала, какие ошибки, что не смогла

## 8002 — ORDER_CHAT
["ollama", "mistral", "github", "zhipu", "gigachat"]

## ТАБЛИЦА: Ошибка → что делать

| Провайдер | Ошибка | Действие |
|-----------|--------|----------|
| **Ollama** | 410 retired | GET /v1/models → найти новую бесплатную модель. Повторить |
| | 403 | Модель платная. Ищи другую из списка |
| | пустой ответ | Модель не даёт вывод на бесплатном. Ищи другую |
| | всё перепробовала | Доложить Олегу |
| **GigaChat** | SSL error | ssl._create_unverified_context(), не httpx |
| | 401 | Получить новый токен через OAuth2 |
| | 429 | Пауза 3с |
| | 400 | Неверный ключ. Проверить base64 |
| | всё перепробовала | Доложить Олегу |
| **Mistral** | 429 | 3 ключа, ротация |
| | 401 | Читать ключ напрямую из .env |
| **GitHub** | 429 | Подождать 60с, жив |
| | 413 | Уменьшить контекст |
| **Zhipu** | 401/пусто | Попробовать urllib, проверить модель |
| **DeepSeek** | 402 | Пополнить баланс. Спросить Олега |
| | 401 | Проверить ключ из .env |
| **OpenRouter** | 403 | IP РФ заблокирован. Доложить Олегу |

## ПРЯМЫЕ ССЫЛКИ
- Ollama: POST https://ollama.com/v1/chat/completions, Bearer
- GigaChat: OAuth2 urllib, skill: gigachat-integration
- Mistral: POST https://api.mistral.ai/v1/chat/completions, Bearer
- GitHub: POST https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21
- Zhipu: POST https://open.bigmodel.cn/api/paas/v4/chat/completions, Bearer

## КЛЮЧИ В .env
/opt/zinaida/.env и /opt/zinaida/meta_agent/.env — читать через open().read(), не через os.getenv
