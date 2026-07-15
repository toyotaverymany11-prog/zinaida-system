# Сессия дизайна VK обложки — 10.07.2026

## Итог: что сработало
- `/opt/zinaida/cover_V2_try2.jpg` (1536×512, 3:1) — победитель
- Текст МЕГАМОЗГ — часть архитектуры здания (вывеска на небоскрёбе)
- Создан через Ideogram V3 Turbo на Replicate
- Для VK: просто ресайз до 1590×400

## Что НЕ сработало (все ошибки сессии)
1. Crop квадрата 1024×1024 → 1590×400 — текст обрезается
2. Растяжение квадрата до 1590×400 — текст сплющивается
3. Чёрный padding — костыль, выглядит как брак
4. PIL/Pillow наложение текста — КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО
5. FLUX Fill (inpainting) — 404 на Replicate
6. Ideogram V3 Turbo с aspect_ratio — 422 ошибка
7. Seedream 5.0 — путает буквы (МЕТАМОЗГ вместо МЕГАМОЗГ)
8. Recraft V3 — врёт про кириллицу

## Ключи/настройки
- FAL_KEY в .env (exhausted balance)
- Hermes config: image_gen.provider: fal, model: fal-ai/ideogram/v3
- Nano Banana 2 — единственная рабочая для кириллицы на Replicate
- Playfair Display TTF: /opt/zinaida/SmmFabrika/assets/fonts/PlayfairDisplay.ttf

## Ошибки агента (не повторять)
- ⚠️ Не использовать PIL/Pillow для текста — Олег в ярости
- ⚠️ Не плодить 8+ попыток если уже есть рабочий файл
- ⚠️ Проверять что файлы cover_V2*.jpg существуют перед новой генерацией
- ⚠️ После генерации проверять через vision_analyze: все буквы в кадре?
