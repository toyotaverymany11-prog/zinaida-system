# Nous Portal API Docs
**Источник:** https://portal.nousresearch.com/api-docs (16.07.2026)
**Статус:** Ключ 401 invalid/out of funds — требуется пополнение

## Ключи
- `/opt/zinaida/.env.nous_key` (основной)
- `/opt/zinaida/.env.nous` — `export NOUS_PORTAL_KEY=...`
- `/opt/zinaida/meta_agent/.env` — `NOUS_PORTAL_KEY=...`
- `/root/.hermes/secrets.env` — # Nous Portal key (получен 15.07.2026 от Олега)

## API
- Базовый URL: `https://inference-api.nousresearch.com/v1`
- Модели: `GET /v1/models` (280 шт)
- Чат: `POST /v1/chat/completions`
- Доки: https://portal.nousresearch.com/api-docs (требует браузер, Vercel Security Checkpoint)
- Подписка: $20/мес Plus — включает 280+ моделей + инструменты (web search, image gen, TTS, browser)

## Бесплатные модели (:free)
- `stepfun/step-3.7-flash:free` — 256K контекст (не работала на практике)
- `tencent/hy3:free` — 262K контекст (HTTP 400)
- **Вывод:** бесплатные модели не работают. Ценность подписки — дешёвый доступ к 280 моделям

## Топ-5 рабочих моделей (проверено 16.07 через curl, до того как ключ протух)
1. `nousresearch/hermes-4-70b` — $0.13/M ✅ русский знает, стоит в 8003
2. `mistralai/mistral-small-3.2-24b-instruct` — ~$0.06/M ✅ лучшая по русскому
3. `deepseek/deepseek-v3.2` — ~$0.50/M ✅ мощная
4. `qwen/qwen3-32b` — ~$0.08/M ✅ 131K контекст
5. `stepfun/step-3.7-flash:free` — $0 ❌ не работала
