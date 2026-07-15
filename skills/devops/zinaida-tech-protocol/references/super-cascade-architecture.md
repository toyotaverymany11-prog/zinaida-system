# Super Cascade — полностью бесплатная каскадная система для 8005

**Дата:** 12.07.2026 (обновлено 13.07.2026)
**Статус:** ✅ ВНЕДРЕНА И РАБОТАЕТ (см. также moa-implementation-pattern.md)

## Цель
95% запросов через бесплатные модели (Mistral + GPT-4o/GitHub), DeepSeek только как запасной. Качество не уступает 8003 (99% через DeepSeek Reasoner за $1.42/M).

## Архитектура

```
Запрос → Ollama (привет/да/нет, 5%, $0)
          → Mistral-large + самооценка
              → CONFIDENCE > 75 → ответ (70%, $0)
              → < 75 → GPT-4o (GitHub, 15%, $0)
                  → ответ или → DeepSeek Flash (8%, $0.27/M)
                      → DeepSeek Pro (2%, $1.42/M)
```

## Замеры моделей (12.07.2026)

| Модель | Время | Качество | Цена |
|--------|-------|----------|------|
| GPT-4o (GitHub) | 2.3с | Уровень DeepSeek Pro | $0 |
| GPT-4o-mini (GitHub) | 2.8с | Хорошо | $0 |
| DeepSeek Reasoner | 3.9с | Отлично | $1.42/M |
| DeepSeek Flash | 4.5с | Отлично | $0.27/M |
| Mistral Large | 4.9с | Уровень DeepSeek Flash | $0 |
| Llama 3.1 405B (GitHub) | ❌ 400 Bad Request | - | $0 |

## GitHub Models

- **Токены:** `GITHUB_TOKEN` (secrets.env) ✅ жив; `GREG_GITHUB_TOKEN` (meta_agent) ❌ 401 мёртв
- **Модели:** gpt-4o, gpt-4o-mini (бесплатно)
- **Rate limit:** ~60 req/min на аккаунт
- **URL:** `https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21`

## Мониторинг (спроектирован)

Роутер слат Telegram-сигналы через `/opt/zinaida/telegram_bot/notify.py`:

| Событие | Действие |
|---------|----------|
| GitHub 429 | → 🚨 лимит + переключение на DeepSeek Flash |
| Все Mistral ключи упали | → ❌ Mistral недоступен |
| DeepSeek баланс < $2 | → ⚠️ пополни |
| Ошибок > 10% | → 🚨 |

## Что уже есть в 8005

- ✅ Классификатор (Ollama → Flash → Pro с порогом 300 символов)
- ✅ Server RAG (rg поиск по файлам сервера)
- ✅ Mistral analyzer (cross-связи файлов)
- ✅ Фикс рода через роутер
- ✅ Ollama для приветствий

## Что нужно добавить

- ❌ Mistral как первый эшелон с самооценкой
- ❌ GPT-4o (GitHub) как второй эшелон
- ❌ Мониторинг с Telegram-сигналами
- ❌ Счётчик запросов для rate limit
