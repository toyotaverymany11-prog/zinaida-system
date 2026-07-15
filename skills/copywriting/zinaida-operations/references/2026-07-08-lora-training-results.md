# LoRA Training Results (2026-07-08)

## Модель

Успешно обучена через Replicate fast-flux-trainer:
- **Модель:** `toyotaverymany11-prog/zina`
- **Версия:** `8ecf86f0e06fd867e2a675d7b9086d9ffc5e5d88cb1882d67da36476c4486638`
- **Триггер:** `ZINAIDA`
- **Фото:** 7 шт, шаги 1000

## Генерация через Python

```python
output = replicate.run('toyotaverymany11-prog/zina:8ecf86f...', input={
    'prompt': 'ZINAIDA, raw portrait...',
    'guidance_scale': 2.0,
    'num_inference_steps': 30
})
```

## Quirk: FileOutput

Replicate Python SDK возвращает `FileOutput`, не строку.
Работает: `output.url` или `str(output)`. Не работает: `output[0]`.

## Проблема: FLUX plastic skin

Решения:
1. RealSkin Pro LoRA (extra_lora)
2. guidance_scale: 1.5-2.5
3. Промпт: raw photo, natural skin, matte finish, no retouching

## Ресурсы

- https://imagera.ai/learn/best-lora-models-realistic-ai-images-2026
- https://replicate.com/blog/using-synthetic-data-to-improve-flux-finetunes
- https://replicate.com/docs/guides/extend/working-with-loras
