# FLUX Plastic Skin — Problem & Solutions

## Проблема

FLUX.1-dev и FLUX.1.1-pro генерируют «пластиковую» кожу: неестественно гладкую, без пор, без текстуры. Особенно заметно на LoRA-тонкой настройке лица.

## Почему так происходит

Это известное ограничение FLUX, связанное с архитектурой модели (rectified flow transformers). Проблема обсуждается на всех форумах: Reddit, Civitai, GitHub issues.

## Решения (от лучшего к худшему)

### Вариант A: RealSkin / No-Plastic-Look LoRA (рекомендуется)

Готовые LoRA для натуральной кожи, комбинируются с нашей через `extra_lora`:

- **RealSkin Pro FLUX** — https://shakker.ai (поиск "RealSkin Pro FLUX")
- **No Plastic-look Skin LoRA** — https://boosty.to/jockerai (бесплатные workflow)
- На Replicate: искать `biggpt1/alin-v2` — фотореалистичная LoRA

Параметры для комбинирования:
```python
output = replicate.run(MODEL, input={
    'prompt': 'ZINAIDA, [trigger_second_lora], portrait...',
    'extra_lora': 'biggpt1/alin-v2',  # вторая LoRA
    'extra_lora_scale': 0.6,  # вес второй LoRA
    'lora_scale': 0.8,  # вес основной LoRA
    'guidance_scale': 2.0
})
```

### Вариант B: Правильные параметры генерации (мы пробовали, стало лучше)

| Параметр | До | После (лучше) |
|----------|----|----------------|
| guidance_scale | 7.5 | **1.5-2.5** |
| num_inference_steps | 30 | **30-50** |
| prompt | без описания | **+ natural skin texture, pores, fine lines, raw photo, no retouching, matte finish** |

Пример рабочего промпта:
```
"ZINAIDA, raw portrait photo, natural skin texture with visible pores, fine lines, realistic skin, matte finish, no retouching, soft natural window light, neutral gray background"
```

### Вариант C: SRPO от Tencent

Модель для улучшения текстуры кожи (47GB). Требует ComfyUI. HuggingFace: `tencent/SRPO`. Есть FP8 дистиллированная версия.

### Вариант D: Комбинация FLUX + SDXL img2img

Сгенерировать через FLUX, потом пропустить через SDXL с low denoising. Требует ComfyUI или второй API.

## Наши тесты (2026-07-08)

- **batch-01** (guidance=2.0, raw prompt): кожа стала заметно натуральнее, поры видны
- **batch-02** (extra_lora alin-v2): не протестирован (упал FileOutput)
- **guidance=1.5**: возможно лучше, но требует отдельного теста

## Ссылки

- https://weirdwonderfulai.art/general/flux-plastic-skin-finally-fixed — SRPO, FP8 для кожи
- https://stable-diffusion-art.com/forums/topic/fix-flux-plastic-skin — обсуждение на форуме
- https://imagera.ai/learn/best-lora-models-realistic-ai-images-2026 — обзор LoRA для кожи
- https://replicate.com/blog/using-synthetic-data-to-improve-flux-finetunes — комбинирование LoRA на Replicate
- https://replicate.com/docs/guides/extend/working-with-loras — Replicate LoRA API
