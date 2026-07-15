# Hermes image_gen plugin для Replicate

**Дата:** 10.07.2026  
**Путь:** `/root/.hermes/plugins/image_gen/replicate/`  
**Конфиг:** `image_gen.provider: replicate` в `/root/.hermes/config.yaml`  
**Токен:** `REPLICATE_API_TOKEN` из `/opt/zinaida/.env`

## Что это

ImageGenProvider-обёртка, которая подключает Replicate API к встроенному тулу `image_generate` в Hermes.

Раньше: я сама дёргала Replicate API из терминала → скрипты → ждала → скачивала.
Теперь: говорю «сгенерируй» → Hermes сам вызывает плагин → ждёт → скачивает.

## Файлы

```
/root/.hermes/plugins/image_gen/replicate/
├── __init__.py   # код провайдера, 9 моделей, ~300 строк
└── plugin.yaml   # манифест (kind: backend, name: replicate)
```

## 9 моделей

| Модель | owner/name | Цена |
|--------|-----------|------|
| flux-dev | black-forest-labs/flux-dev | $0.025 |
| flux-schnell | black-forest-labs/flux-schnell | $0.003 |
| flux-1.1-pro | black-forest-labs/flux-1.1-pro | $0.05 |
| recraft-v3 | recraft-ai/recraft-v3 | $0.04 |
| ideogram-v3 | ideogram-ai/ideogram-v3 | $0.08 |
| ideogram-v3-turbo | ideogram-ai/ideogram-v3-turbo | $0.03 |
| ip-adapter-face-id | fofr/ip-adapter-face-id | ~$0.01 |
| sdxl-ip-adapter-face-id | fofr/sdxl-ip-adapter-face-id | ~$0.01 |
| ip-adapter-faceid-plusv2 | tencentarc/ip-adapter-face-id-plusv2 | ~$0.01 |

## Питфоллы (из опыта разработки)

1. **`error_response()` — только keyword-only:**
   - Правильно: `error_response(error="текст", provider="replicate", prompt=prompt)`
   - Неправильно: `error_response("текст", provider="replicate")` → TypeError

2. **`success_response()` — аргумент `image=`, не `image_path=`:**
   - Правильно: `success_response(image=tmp.name, model=..., prompt=..., aspect_ratio=..., provider=...)`
   - Неправильно: `success_response(image_path=tmp.name, ...)`

3. **Плагины кэшируются Gateway в памяти.**
   Простое `pkill hermes-gateway` может не помочь — остаётся старый байткэш.
   Жёсткий рестарт:
   ```bash
   pkill -9 -f hermes-gateway
   rm -rf /root/.hermes/plugins/image_gen/*/__pycache__
   cd /usr/local/lib/hermes-agent
   npx hermes gateway start --port 8642 --daemon
   ```

4. **Hermes Studio (веб-интерфейс) использует bridge-worker** — может не видеть новый плагин даже после рестарта Gateway. Нужен `/reset` сессии.

5. **FAL провайдер перехватывает фолбэк:** Если плагин не зарегистрировался (например, из-за TypeError), `get_active_provider()` находит FAL (потому что `FAL_KEY` есть) и тихо фолбечится на него. Если FAL падает — ошибка выглядит как плагин сломан. Решение: убедиться что FAL_KEY не активен или что плагин регистрируется корректно.

6. **Регистрация плагина требует наследования `ImageGenProvider`.**
   ```python
   from agent.image_gen_provider import ImageGenProvider, error_response, success_response
   
   class MyProvider(ImageGenProvider):  # обязательно
       ...
   
   def register(ctx):
       ctx.register_image_gen_provider(MyProvider())
   ```

## Что НЕ умеет плагин

- LoRA-модели (ZINAIDA trigger_word) — для них через `replicate-image-gen` навык с полным контролем параметров
- Кастомные параметры генерации (guidance, num_inference_steps, negative_prompt) — image_generate тул их не передаёт
- Загрузка нескольких reference изображений (только 1)
