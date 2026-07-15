# VK обложка — рабочий процесс (v3, 10.07.2026, исправлено)

## Размер
**1590×400 px** — десктопная обложка сообщества VK (~4:1).

## Эталонный результат
**`/opt/zinaida/vk_cover_arch.jpg`** (1024×1024) — небоскрёб снизу вверх, золотой МЕГАМОЗГ наверху, «читаю мужиков как код», «AI психоаналитик». ✅ УТВЕРЖДЁН Олегом 10.07.2026.

**Что в нём правильно:**
- Золотые буквы МЕГАМОЗГ на небоскрёбе — доминируют
- Sans-serif шрифт (не serif!)
- Ракурс снизу вверх (low angle) — драматичный
- Все 3 надписи в кадре
- Фотореализм, не графика

**❌ ОТВЕРГНУТ:** `cover_V2_try2.jpg` — serif на skyline. Олег: «говно собачье».

## Модель
**Nano Banana 2** (`google/nano-banana-2`) через Replicate HTTP API.
- 🏆 Лучшая кириллица (буква Г на месте, не заменяется на G)
- Время: 5-10 секунд
- Цена: $0.035/шт
- **Всегда выдаёт 1024×1024** — width/height ИГНОРИРУЮТСЯ

## Проблема: квадрат → wide формат
Nano Banana 2 всегда выдаёт квадрат 1024×1024. Для VK обложки 1590×400 нужно:

**Правильное решение: промпт с текстом ПО ЦЕНТРУ + crop центральной полосы 256px (4:1) + ресайз до 1590×400.**

## Промпт для текста по центру (crop-ready)
```text
A modern skyscraper at night with a large golden sign МЕГАМОЗГ in the exact center of the image on the building facade, below it centered text читаю мужиков как код, below that AI психоаналитик, the sign is perfectly centered vertically at 50 percent height, lots of empty space above the text and below the text for cropping, dark blue sky, cinematic photorealistic style, square 1:1
```

Ключевые фразы:
- «centered vertically at 50 percent height»
- «lots of empty space above and below the text for cropping»

## Post-processing (Pillow) — ТОЛЬКО crop + resize
```python
from PIL import Image
im = Image.open("nano_output.jpg")  # 1024×1024
w, h = im.size
target_h = w // 4    # 256px для 4:1
top = (h - target_h) // 2
cropped = im.crop((0, top, w, top + target_h))  # 1024×256
resized = cropped.resize((1590, 400), Image.LANCZOS)
resized.save("vk_cover_final.jpg", quality=95)
```

## Проверка через vision_analyze (ОБЯЗАТЕЛЬНО)
Перед отправкой Олегу:
- МЕГАМОЗГ — полностью в кадре
- «читаю мужиков как код» — полностью
- AI психоаналитик — полностью
- Размер — 1590×400
- Текст НЕ растянут, НЕ искажён

## 💩 Что НЕ РАБОТАЕТ (проверено многократно)
1. ❌ Padding + resize — текст растянут, «дёшево»
2. ❌ Crop от центра без проверки — текст обрезан
3. ❌ Промпт без указания «центр + пустота» — текст внизу, crop невозможен
4. ❌ FLUX Dev — не умеет кириллицу без LoRA
5. ❌ Recraft V3 — пишет латиницей по-английски
6. ❌ Seedream 5.0 — путает буквы (МЕТА вместо МЕГА)
7. ❌ Простой resize 1024→1590 — сплющивает текст

## ⚡ Альтернатива: Ideogram V3 Turbo
Если Nano Banana 2 не даёт нужного wide-формата:
- Модель: `ideogram-ai/ideogram-v3-turbo`
- aspect_ratio: `'3:1'` 
- magic_prompt_option: `'Auto'` (строго с большой A, иначе 422)
- Даёт 1536×512 — просто ресайз до 1590×400
- Кириллица ~90-95% — проверить через vision

## Быстрый старт
1. Проверить `/opt/zinaida/cover_*.jpg` и `vk_cover_*.jpg` — может, уже есть
2. Сверить с `references/vk-cover-inventory.md` — какая оценка Олега
3. Если нет готового → Nano Banana 2 с промптом «текст по центру + пустота»
4. Crop центра 256px → ресайз до 1590×400
5. Проверка vision_analyze
6. Показать Олегу, зафиксировать его оценку в `design_feedback.md` СРАЗУ
