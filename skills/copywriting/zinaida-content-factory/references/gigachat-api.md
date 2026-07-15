# GigaChat API (Сбер)

**Статус:** ✅ Активен в роутере как провайдер.
**Ключ:** `GIGACHAT_AUTH_KEY` в `/opt/zinaida/config/secrets.env`
**Документация:** `/opt/zinaida/inbox/GigaChat_API.md`

## Как работает
1. OAuth: POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth (токен 30 мин)
2. API: https://gigachat.devices.sberbank.ru/api/v1/chat/completions
3. Vision: через загрузку файла + attachments (не image_url)
4. SDK: `pip install gigachat`, `verify_ssl_certs=False`

## Модели
- GigaChat (базовая) — бесплатно, текст
- GigaChat-2-Max — платно (402), текст + vision

## Цепочка в роутере
`zhipu → gigachat → ollama` (для простых запросов)
