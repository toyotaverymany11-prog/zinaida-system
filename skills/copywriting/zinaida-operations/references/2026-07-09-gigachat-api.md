# GigaChat API (Сбер) — разобрано 2026-07-09

## Документация
- Основная инструкция: https://geoscout.pro/ru/blog/gigachat-api-instrukciya
- Видео-туториал по работе с изображениями: https://youtu.be/7mRdG_ocEQY (код: https://github.com/trashchenkov/gigachat_tutorials)
- Документация Сбера: https://developers.sber.ru/docs/ru/gigachat/guides/images-generation
- LiteLLM-GigaChat: https://docs.litellm.ai/docs/providers/gigachat

## Процесс работы
1. Получить OAuth токен: POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth
   - Authorization: Basic base64(client_id:client_secret)
   - scope=GIGACHAT_API_PERS (физлица)
   - RqUID: uuid4
   - Токен живёт 30 минут, нужен refresh
2. Использовать токен для всех запросов к API

## Загрузка изображений (не OpenAI формат!)
GigaChat НЕ поддерживает image_url в content. Вместо этого:
1. Загрузить файл через POST /v1/files (multipart)
2. Получить file_id
3. Передать в attachments при chat completion

Формат:
```python
from gigachat import GigaChat
giga = GigaChat(credentials="ключ", scope="GIGACHAT_API_PERS", verify_ssl_certs=False)
file_info = giga.upload_file(open('photo.jpg', 'rb'))
resp = giga.chat({
    "model": "GigaChat-2-Max",
    "messages": [{
        "role": "user",
        "content": "Опиши изображение",
        "attachments": [file_info.id_]
    }]
})
```

## Модели и vision
- GigaChat-2-Max / GigaChat-2-Pro — поддерживают vision (но платные, 402)
- GigaChat (базовая), GigaChat-Plus, GigaChat-Pro — текст, бесплатно
- Бесплатный тариф НЕ даёт vision

## Важные нюансы
- Сертификаты самоподписанные — нужен verify_ssl_certs=False
- Работает из РФ без VPN
- Соответствие 152-ФЗ
- Python SDK: `pip install gigachat`
- Ключ хранится в `/opt/zinaida/config/secrets.env` (GIGACHAT_AUTH_KEY)
- Документация: `/opt/zinaida/inbox/GigaChat_API.md`
