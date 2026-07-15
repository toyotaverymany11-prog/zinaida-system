# VK обложка через Nano Banana 2 — рабочий процесс
Дата: 2026-07-10
Модель: google/nano-banana-2
Время генерации: 5 секунд
Результат: ✅ идеальная кириллица, 3 текстовых элемента

## Проблема
Олег хотел VK обложку с:
1. Крупной вывеской «МЕГАМОЗГ» на небоскрёбе (золотой serif, доминирует)
2. Размытой надписью «AI психоаналитик» сбоку, вдали, полупрозрачно
3. Мелкой подписью «читаю мужиков как код» снизу

Предыдущие попытки через Ideogram, Recraft, FLUX не давали одновременно и идеальную кириллицу, и правильную композицию из 3 элементов.

## Решение
Nano Banana 2 (google/nano-banana-2) — модель, которая в тестах 09.07 дала лучшую кириллицу.

## Промпт (проверен, работает)
```python
prompt = """Panoramic city skyline view at dusk from high angle. At the roof of a VERY tall skyscraper in the center, extremely large glowing golden serif letters МЕГАМОЗГ as an architectural landmark sign, dominating the frame. Letters are very bold, prominent, taking up the top third of the building. On the side of the same building, subtle blurred text "AI психоаналитик" in elegant gray, appearing distant and faint, partially hidden by haze. Beneath МЕГАМОЗГ in smaller elegant white serif: читаю мужиков как код. Warm amber city lights reflecting on buildings, cinematic photography, photorealistic, premium quality, wide panoramic view, foggy atmospheric haze, sharp focus on the main sign"""
```

## ⚠️ ПИТФОЛЛ: width/height ИГНОРИРУЮТСЯ
Nano Banana 2 на Replicate **ВСЕГДА возвращает 1024×1024**, независимо от переданных width/height.
Это не баг — это особенность Replicate-обёртки модели.

**Что НЕ работает:** передача width=1590, height=400 напрямую в модель.
**Что работает:** генерация в 1024×1024 → пост-обработка через Pillow (crop + resize).

## Пост-обработка: crop до 1590×400
```python
from PIL import Image
im = Image.open('vk_cover_1024.jpg')
target_w, target_h = 1590, 400
crop_w = 1024
crop_h = int(crop_w * target_h / target_w)  # ~258
left = 0
top = (1024 - crop_h) // 2
cropped = im.crop((left, top, left + crop_w, top + crop_h))
resized = cropped.resize((target_w, target_h), Image.LANCZOS)
resized.save('vk_cover_final_1590.jpg', quality=95)
```

Это **техническая операция** (изменение размера под формат платформы), не творческий дизайн.
Pillow для этого разрешён (правило запрещает творческий дизайн через Pillow, не техобработку).

## Другие модели — та же проблема
- **Seedream 5.0 Lite** — всегда выдаёт 2048×2048, игнорирует width/height
- **Ideogram V3 Turbo** — поддерживает aspect_ratio через Replicate (проверять отдельно)

Решение для всех: генерировать в нативном размере модели, потом обрезать.

## Ключевые фишки промпта
1. **«VERY tall» + «extremely large»** — управляет размером текста на здании (Nano Banana понимает усилители)
2. **«subtle blurred ... in elegant gray, appearing distant and faint, partially hidden by haze»** — создаёт размытую надпись сбоку, не конкурирующую с главной
3. **Три элемента явно прописаны** в порядке приоритета: МЕГАМОЗГ → AI психоаналитик → читаю мужиков как код
4. **Английский промпт** — Nano Banana 2 понимает только английский, кириллицу в кавычках рендерит правильно

## Результат проверки через vision_analyze
- ✅ МЕГАМОЗГ — крупно, золотой serif, буква Г на месте
- ✅ «читаю мужиков как код» — снизу, читается
- ✅ «AI психоаналитик» — сбоку, размытый
- ✅ Общий стиль — кинематографичный, тёплая гамма

## Файлы
- `/opt/zinaida/vk_cover_nano2.jpg` — исходник 1024×1024 (успешная генерация)
- `/opt/zinaida/vk_cover_final_1590.jpg` — финал 1590×400 (после crop)
- `/opt/zinaida/vk_cover_seedream_1590.jpg` — Seedream вариант (МЕТАМОЗГ вместо МЕГАМОЗГ — ошибка модели)
