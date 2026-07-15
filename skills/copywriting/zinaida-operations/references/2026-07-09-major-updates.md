# Сессия 2026-07-09: ключевые изменения

## 1. Роутер Zinaida-Router — новая цепочка провайдеров
Файл: `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`

**Было:** `ORDER_CHAT = ["deepseek_flash"]` — только DeepSeek Flash
**Стало:** `ORDER_CHAT = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]`

- Mistral — основной провайдер (2 ключа, ротация по лимитам). Модель изменена с `mistral-small-latest` на `mistral-large-latest`.
- GigaChat — изменена модель с платной `GigaChat-Max` на бесплатную `GigaChat` (только текст). GigaChat использует OAuth-токен (живёт 30 мин), самоподписанный сертификат (verify_ssl_certs=False).
- DeepSeek Flash — платный, теперь в самом конце как запасной.

## 2. Vision-прокси: GitHub → Mistral → Ollama
Скрипт: `/opt/zinaida/scripts/vision_fallback_proxy.py`, порт 8901, systemd: vision-proxy.service

**Было:** GitHub → Ollama (2 звена)
**Стало:** GitHub → Mistral → Ollama (3 звена)

- GitHub (gpt-4o-mini): быстрее всех (~10 сек)
- Mistral (mistral-large-latest): самый подробный (~18 сек). **ВАЖНО:** Mistral использует brotli-сжатие -> обязательно передавать `Accept-Encoding: identity`, иначе ошибка декодирования.
- Ollama (gemma3:27b, 3 ключа): fallback

**Сравнение моделей (тест на одном скриншоте):**
| Модель | Время | Символов |
|--------|-------|----------|
| GPT-4o-mini | 10.3 сек | 1230 |
| Mistral Large | 18.4 сек | 1640 |
| Gemma 3 27B | 20.9 сек | 1432 |

## 3. Telegram бот — 401 ошибка и порт
Бот стучался на gateway (8642), который требует API-ключ. Исправлено: bot.py теперь стучится на Zinaida-Router (8002) с `dummy-key`, модель `Zinaida-Router` вместо `zinaida`.

## 4. Консилиум — очистка markdown
Перед отправкой в Telegram текст очищается от markdown-символов (***, [], ``, ###) через strip_md().

## 5. GigaChat — только бесплатная модель
Изменена модель с `GigaChat-Max` (402 Payment Required) на `GigaChat` (бесплатный текст).

## 6. Mistral — 2 ключа с ротацией
Добавлены в .env и secrets.env:
- MISTRAL_API_KEY: ITTNRjD0JrGQVUpTlKum97yoV0yAROAb
- MISTRAL_API_KEY_2: 4PGuqi4DpRHIn4A0Suw8w73PEom6XV0p

`mistral-large-latest` поддерживает vision (image_url в content).

## 7. Лера — починка Kanban crash
Причина: `hermes` не найден в PATH при старте Kanban-воркера. Исправлено: `systemctl set-environment PATH=...`

## 8. Design feedback
Все оценки Олега по дизайну теперь записываются в `/opt/zinaida/shared_memory/design_feedback.md`.

## 9. Созданный навык
`zinaida-replicate-api` (mlops) — правильные HTTP-запросы к Replicate API вместо сломанной Python-библиотеки.
