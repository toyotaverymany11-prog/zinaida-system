# Replicate Access: Auth Quirks (2026-07-08)

## Токены на аккаунте

На replicate.com/account/api-tokens есть 3 токена:
- **Zina2** — `r8_QZWTjkMnYM5LRtnRIz8xz9X3Q0zghkL3u5eXs` (используется в secrets.env)
- **Zina** — `r8_Ffo...` (не используется)
- **Default** — `r8_UnG...` (не используется)

Все токены имеют одинаковые права. При создании нового через UI — нет выбора скоупов/разрешений.

## Что работает

| Операция | Статус | Метод |
|----------|--------|-------|
| GET /v1/models/{model} (публичные) | ✅ 200 | Bearer |
| POST /v1/models (создание) | ❌ 403 error code 1010 | Bearer или Token |
| GET /v1/account | ❌ 403 | Bearer |
| POST /v1/predictions (inference) | ✅ 200 | Bearer |
| replicate.models.create() (Python lib) | ❌ 403 — wrong owner | Через библиотеку |
| replicate.models.list() (Python lib) | ✅ 200 | Через библиотеку |
| curl с полным токеном | ✅ 200 | Bearer в header |

## Ключевые находки

1. **replicate Python библиотека** проходит аутентификацию там, где прямой API даёт 403. Это значит токен ВАЛИДЕН, но owner должен быть правильным (реальный username на Replicate).

2. **Owner 'zinaida' — неправильный.** Нужен реальный username аккаунта. Как узнать: на replicate.com в правом верхнем углу или в URL профиля.

3. **Создание модели через API невозможно без знания username.** Решение: веб-интерфейс replicate.com/create.

4. **После создания модели через веб**, её можно использовать через API с тем же токеном:
   - Загрузить zip: `POST /v1/files` (multipart/form-data)
   - Запустить training: `POST /v1/models/replicate/fast-flux-trainer/versions/{version}/trainings`
   - Проверить статус: `GET /v1/trainings/{id}`

5. **Error code 1010** = нет прав на операцию для этого аккаунта/токена.
