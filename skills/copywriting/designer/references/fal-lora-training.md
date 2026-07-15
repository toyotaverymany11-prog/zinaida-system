# FAL LoRA Training — Face Dataset (12.07.2026)

## LoRA URL (обучена 12.07.2026)
```
https://v3b.fal.media/files/b/0aa1ef03/vcaC2BHukEixgZekjHkZL_pytorch_lora_weights.safetensors
```
Trigger word: `zinaida`
Стоимость обучения: $2 (1000 steps)
Остаток на FAL: ~$7.88

## Датасет (23 фото)
Правильная папка: `/opt/zinaida/SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/`
- zinaida_01.jpg ... zinaida_09_minimal.jpg
- zinaida_fullbody_*.jpg (5 шт)
- zinaida_halfbody_*.jpg (3 шт)
- test_skin.jpg

## Процесс обучения
```python
import fal_client
import os
os.environ['FAL_KEY'] = '...'

# Загрузить ZIP
url = fal_client.upload_file('/tmp/zinaida_training.zip')

# Запустить обучение
result = fal_client.subscribe('fal-ai/flux-lora-fast-training', arguments={
    'images_data_url': url,
    'trigger_word': 'zinaida',
    'is_style': False,   # False = лицо, True = стиль
    'steps': 1000
})
```

## Использование
```python
result = fal_client.subscribe('fal-ai/flux-lora', arguments={
    'prompt': 'portrait of a zinaida woman, ...',
    'loras': [{'path': LORA_URL, 'scale': 0.6}],
    'guidance_scale': 1.5,
    'num_inference_steps': 30,
    'image_size': 'square_hd'
})
```

## Питфоллы
- Data URL в `images_data_url` слишком длинный (>4MB base64) — FAL выдаёт 422. Использовать `fal_client.upload_file()`
- `storage.fal.ai` не резолвится с сервера — не ходить напрямую
- FLUX не умеет кириллицу — текст через GPT Image 2 отдельно
- LoRA scale 1.0 = пластиковое лицо. Scale 0.6 = реалистичнее
