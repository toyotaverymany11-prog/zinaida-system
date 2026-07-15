# FAL Model Workflow: Zinaida + Text on Image

**Проблема:** Нужно получить изображение с лицом Зинаиды И кириллическим текстом.
**Модели:** GPT Image 2 (текст) vs FLUX LoRA (лицо). Несовместимы напрямую.

## Вариант A: GPT Image 2 с описанием Зинаиды (🏆 предпочтительный)

**Когда:** Нужна картинка с текстом + портрет, лицо не обязано быть точной Зинаидой

**Промпт:**
```
Fashion magazine cover. Black background, dramatic vibrant red abstract brushstrokes like paint splashes. Portrait of a beautiful young Russian woman, 28 years old, with long dark brown wavy hair, fair skin, dark eyes, serious confident expression, red lipstick, elegant dark clothing. Large bold white serif Cyrillic text at top center: [ТЕКСТ ЗАГОЛОВКА]. Smaller white Cyrillic serif text at bottom: [ТЕКСТ ПОДЗАГОЛОВКА]. Cinematic dramatic lighting, high contrast, dark moody editorial style. Only black red white colors. Professional magazine cover.
```

**FAL API запрос:**
```bash
curl -s -X POST https://queue.fal.run/fal-ai/gpt-image-2 \
  -H "Authorization: Key ${FAL_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "...",
    "image_size": {"width": 1080, "height": 1350}
  }'
```

**Получить результат:**
```bash
curl -s "https://queue.fal.run/fal-ai/gpt-image-2/requests/<REQUEST_ID>" \
  -H "Authorization: Key ${FAL_KEY}"
# Ответ: {"images": [{"url": "https://v3b.fal.media/..."}]}
```

**Время:** ~20-60 секунд. Если долго — ждать до 90 секунд.

## Вариант B: FLUX + LoRA (точное лицо Зинаиды, без текста)

**Когда:** Нужно ТОЧНОЕ лицо Зинаиды для референса или отдельного элемента

**Промпт с trigger word `zinaida`:**
```
portrait of zinaida, young woman 28 years old with dark brown wavy hair, serious confident expression, looking directly at camera, black background, dramatic cinematic Rembrandt lighting, dark red lipstick, elegant, high contrast, fashion editorial style
```

**API запрос:**
```bash
curl -s -X POST https://queue.fal.run/fal-ai/flux-lora \
  -H "Authorization: Key ${FAL_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "portrait of zinaida, ...",
    "image_size": "square_hd",
    "num_images": 1,
    "lora_scale": 0.6,
    "enable_safety_checker": false
  }'
```

**Время:** ~10-15 секунд

## Вариант C: FLUX LoRA лицо → GPT Image 2 edit добавить текст (НЕ РАБОТАЕТ)

Пытались: GPT Image 2 edit endpoint (`/fal-ai/gpt-image-2/edit`) не отвечает. 
Пытались: Ideogram V3 с image_url — даёт ошибки в кириллице и меняет изображение.
Пытались: GPT Image 2 с `image_url` и `strength` — параметры игнорируются.

**Вывод:** Композиция из двух разных моделей НЕВОЗМОЖНА без PIL/Pillow (запрещён).

## Чек-лист при генерации с лицом

- [ ] Промпт НЕ содержит «blonde» если нужна Зинаида — у неё тёмные волосы
- [ ] Описание: «молодая русская, 28 лет, тёмные волнистые волосы, светлая кожа, тёмные глаза»
- [ ] Цвета: чёрный + красный + белый (для Instagram трека ЦУКОЙ)
- [ ] Кириллица в промпте явно указана: «Cyrillic text in large bold white serif»
- [ ] Текст на русском проверен на ошибки ДО отправки
- [ ] После получения: vision_analyze с проверкой кириллицы побуквенно

## FAL KEY
```
8e995491-ebb0-4650-8f66-dd0c2dee09ef:4fb8fc63694193ad8463f04ad9b25c1f
```
