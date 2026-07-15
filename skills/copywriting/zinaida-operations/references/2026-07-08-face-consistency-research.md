# Face Consistency Research (2026-07-08)

## Проблема
Flux-1.1-pro не сохраняет лицо при генерации. Нужна модель, которая понимает "это тот же человек".

## Модели на Replicate для consistent characters

Из блога Replicate (https://replicate.com/blog/generate-consistent-characters):

| Модель | Цена/изобр | Скорость | Доступ |
|--------|-----------|---------|--------|
| OpenAI gpt-image-1 | $0.04-0.17 | 16-59s | ❌ 403 |
| Runway Gen-4 Image | $0.05-0.08 | 20-27s | ❌ 403 |
| FLUX.1 Kontext Pro | $0.04 | 5s | ❌ 403 |
| FLUX.1 Kontext Dev | $0.025 | 4s | ❌ 403 |
| Bytedance SeedEdit 3 | $0.03 | 13s | ❌ 403 |
| FLUX.2 Pro (8 ref images) | ? | ? | ❌ 403 |
| FLUX.2 Dev (10 ref images) | ? | ? | ❌ 403 |

## Баланс аккаунта: ~$10

На Replicate-аккаунте есть около $10. Этого хватает на:
- 1 LoRA fine-tuning (~$1.46-2.00)
- + ~300-400 генераций через flux-dev (~$0.025/изобр)
- Или запуск Kontext Dev (~$0.025/изобр × 300 = $7.50)

## Fine-tuning (LoRA) — рекомендованный подход

Блог: https://replicate.com/blog/fine-tune-flux-with-an-api

Процесс:
1. Собрать 10+ фото в zip
2. Создать destination model: `POST /v1/models` с owner, name, hardware
3. Загрузить zip: `POST /v1/files` (multipart)
4. Запустить training: `POST /v1/models/ostris/flux-dev-lora-trainer/versions/<id>/trainings`
   - `destination`: owner/model-name
   - `input.input_images`: url из шага 3
   - `input.trigger_word`: уникальное слово (например ZINAIDA_FACE)
5. После обучения — генерировать через созданную модель с trigger word в промпте

Стоимость: ~$2 за 20 мин обучения (H100 GPU).

### Тренировка через веб-интерфейс (если API даёт 403)

Из-за ограничений API-токена (403 error code 1010) создание модели и запуск тренировки может не работать через API.
Альтернатива — веб-форма: https://replicate.com/replicate/fast-flux-trainer/train
Нужно:
1. Залогиниться на replicate.com (вручную)
2. Создать destination model (например `zinaida/zinaida-face-lora`)
3. Загрузить zip с фото
4. Указать trigger_word = `ZINAIDA_FACE`
5. lora_type = `subject`
6. Нажать Create training

Или сгенерировать новый API-токен с полными правами на replicate.com/account/api-tokens.

## Replicate API endpoints

- GET /v1/models/{owner}/{name} — информация о модели
- POST /v1/models/{owner}/{name}/predictions — запуск генерации
- GET /v1/predictions/{id} — статус генерации
- POST /v1/files — загрузка файла (multipart)
- POST /v1/models — создание модели
- POST /v1/models/{owner}/{name}/versions/{version}/trainings — запуск обучения

## Проверка доступности модели

```python
import urllib.request, json
with open('/opt/zinaida/config/secrets.env') as f:
    for line in f:
        if 'REPLICATE_API_TOKEN' in line:
            token = line.strip().split('=', 1)[1]; break
req = urllib.request.Request('https://api.replicate.com/v1/models/{name}', headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req)
print(json.loads(resp.read()).get('name'))
```

## Альтернативы Replicate

- GitHub Models: gpt-4o-mini (текст), нет image generation
- Ollama Cloud: gemma3:27b (vision), нет image generation
- Hugging Face Inference API: много моделей, может быть бесплатно
- ComfyUI локально: самый гибкий, но требует GPU
