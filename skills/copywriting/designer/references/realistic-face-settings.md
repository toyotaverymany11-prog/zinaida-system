# Realistic Face Settings for FLUX LoRA (12.07.2026)

## ПРОБЛЕМА

FLUX Dev + LoRA даёт "пластиковое" лицо — кожа выглядит искусственно, без пор, без текстуры. Олег: «лицо пластиковое, ненастоящее».

## РЕШЕНИЕ (3 версии, проверено 12.07.2026)

Настройки для генерации лица Зинаиды через FAL (`fal-ai/flux-lora`):

| Параметр | V1 ❌ пластик | V2 ⚠️ средне | V3 🏆 ЛУЧШАЯ |
|----------|--------------|-------------|--------------|
| LoRA scale | 1.0 | 0.85 | **0.6** |
| guidance_scale | 3.5 | 2.0 | **1.5** |
| num_inference_steps | 28 | 30 | 30 |
| seed | random | 42 | **777** |
| Negative prompt | нет | короткий | **агрессивный** |

### V3 (победившая)

```python
result = fal_client.subscribe('fal-ai/flux-lora', arguments={
    'prompt': 'Professional portrait photo of zinaida woman, 30 years old, blonde hair, blue eyes, natural makeup, black turtleneck, dark background. Real human skin texture, visible pores, fine wrinkles, natural imperfections, skin details, cinematic photography, sharp focus, depth of field',
    'negative_prompt': 'plastic, smooth, airbrushed, flawless, cgi, render, 3d, digital art, painting, illustration, fake skin, instagram filter, beauty filter, porcelain skin, wax skin, mannequin, doll, synthetic',
    'loras': [{'path': LORA_URL, 'scale': 0.6}],
    'num_images': 1,
    'guidance_scale': 1.5,
    'num_inference_steps': 30,
    'image_size': 'square_hd',
    'seed': 777
})
```

### Почему работает

- **LoRA scale 0.6** (не 1.0): Чем выше scale, тем сильнее модель «заучивает» черты, теряя вариативность и естественность. 0.6 даёт баланс между узнаваемостью и реалистичностью.
- **guidance_scale 1.5** (не 3.5): Низкий guidance даёт модели больше свободы. Высокий guidance форсирует "идеальное" лицо = пластик.
- **Negative prompt агрессивный**: "plastic, smooth, airbrushed, wax skin, mannequin, doll, synthetic" — явно уводит от AI-эстетики.
- **Seed**: менять при каждой попытке (444, 777, 123, 42).

### Визуальная разница

| Версия | Оценка Олега | Описание |
|--------|-------------|----------|
| V1 (scale 1.0) | ❌ «пластик» | Гладкая кожа, пор нет, CGI-эффект |
| V3 (scale 0.6) | ✅ «так лучше» | Кожа натуральная, текстура есть, реалистично |

## ВЫВОД

Настройки по умолчанию на FAL (scale=1.0, guidance=3.5) дают пластик. 
**Для реалистичного лица всегда снижать scale до 0.6 и guidance до 1.5.**
