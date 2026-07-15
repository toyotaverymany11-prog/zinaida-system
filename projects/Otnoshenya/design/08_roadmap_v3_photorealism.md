# ДОРОЖНАЯ КАРТА — ВАРИАНТ 3: ФОТОРЕАЛИЗМ
Версия: 1.0 | Дата: 2026-07-10
Автор: Зинаида
Статус: ✅ Выбран Олегом

---

## ПОЧЕМУ ВАРИАНТ 3 — ЭТО ПРАВИЛЬНЫЙ ВЫБОР

**Проблема кириллицы снята.** В Варианте 3 текст идёт в caption поста, не на картинке. Значит:
- Не нужно мучиться с Recraft/Seedream/кириллицей в диффузионных моделях
- FLUX Dev без LoRA текста = идеальный фотореализм за $0.025
- Нет ограничений по длине текста (в caption можно писать что угодно)
- Алгоритмы Instagram любят текст в caption (SEO, ключевые слова)

**Тренд 2026:** эмоциональные фотореалистичные сцены > студийная графика.
ЦА (женщины 18-40) больше реагирует на «узнаваемую ситуацию», чем на красивую обложку.

---

## ТРИ НАПРАВЛЕНИЯ ТЕСТОВ

### Направление A: Мужские типажи
**Модель:** `black-forest-labs/flux-dev` (без LoRA, чистый FLUX)
**Размер:** 1080×1080
**Количество:** 4 типажа × 3 генерации = 12 картинок
**Бюджет:** ~$0.30

| Типаж | Описание | Поза | Свет | Эмоция |
|-------|----------|------|------|--------|
| A1 «Альфа» | Мужчина 35, костюм/рубашка, уверенный | Стоит у окна, руки в карманах | Холодный, контрастный | Уверенность, контроль |
| A2 «Ранимый» | Мужчина 30, домашняя одежда | Сидит на краю кровати, смотрит в пол | Тёплый, приглушённый | Растерянность, тоска |
| A3 «Токсичный» | Мужчина 35-40, тёмная одежда | Полуоборот, отворачивается от камеры | Резкие тени, noir | Агрессия, холод |
| A4 «Любящий» | Мужчина 30-35, свитер/ casual | Тянет руку, мягкая улыбка | Golden hour, мягкий | Нежность, тепло |

### Направление B: Сцены с парой
**Модель:** `black-forest-labs/flux-dev`
**Размер:** 1080×1080
**Количество:** 3 сценария × 3 генерации = 9 картинок
**Бюджет:** ~$0.23

| Сценарий | Описание | Композиция | Вайб |
|----------|----------|------------|------|
| B1 «Отдаление» | Пара сидит спиной друг к другу на диване | Два силуэта, между ними пустота | Холод, разрыв |
| B2 «Протянутая рука» | Он тянет руку, она отвернулась | Рука на переднем плане, она в глубине | Надежда, боль |
| B3 «Прощание» | Он стоит у двери, она сидит на кровати | Дверной проём как рамка | Грусть, конец |

### Направление C: Портреты Зинаиды (для будущих обложек Варианта 1)
**Модель:** `black-forest-labs/flux-dev` + LoRA `toyotaverymany11-prog/zina`
**Стиль:** Ч/б, тёмный фон, свободное место для текста (верх 60%)
**Размер:** 1080×1080
**Количество:** 5 портретов
**Бюджет:** ~$0.13

| Портрет | Эмоция | Кадрирование | Комментарий |
|---------|--------|-------------|-------------|
| C1 | Серьёзная, прямой взгляд | От плеч | Основной, для обложек |
| C2 | Лёгкая улыбка | Поясной | Для тёплых тем |
| C3 | Задумчивая, взгляд вбок | От плеч | Для экспертности |
| C4 | Ироничная, полуулыбка | Поясной | Для провокаций |
| C5 | Уверенная, chin up | От груди | Для сильных заявлений |

---

## ЧТО ДЕЛАЕМ НЕПОСРЕДСТВЕННО СЕЙЧАС

### Шаг 1: Генерация всех 3 направлений через Replicate API
- 12 + 9 + 5 = 26 картинок
- Бюджет: ~$0.66
- Время: ~3-5 минут на все генерации
- Результаты складываются в `/opt/zinaida/design/generated/batch_20260710/`

### Шаг 2: Я проверяю
- Открываю каждую картинку
- Смотрю: качество, эмоция, композиция, реализм
- Отбраковываю явный брак

### Шаг 3: Показываю Олегу
- 3 направления = 3 папки (A, B, C)
- В каждой — лучшие 2-3 варианта
- Олег выбирает цифрой: «А2», «B1», «C3»

### Шаг 4: Утверждение
- Лучшие картинки → `approved/`
- Запоминаем какие промпты сработали
- Корректируем для продакшена

### Шаг 5: Контент-план
- Запускаем производство с утверждёнными промптами
- Каждый пост в теме → выбираем типаж под тему
- Текст в caption (контент-завод генерирует)

---

## ПРОМПТЫ ДЛЯ ГЕНЕРАЦИИ (ГОТОВЫЕ)

### A1 — Альфа
```
cinematic photorealism, medium shot of a confident man 35 years old in a tailored suit, standing by a large window in a modern apartment, city lights visible, hands in pockets, direct confident gaze, cold color palette, blue/grey tones, shallow depth of field, bokeh background, sharp focus on face, natural lighting from window, photorealistic, 8k, --ar 1:1
```

### A2 — Ранимый
```
cinematic photorealism, medium shot of a thoughtful man 30 years old in a soft sweater, sitting on the edge of an unmade bed, head slightly down, looking at the floor, warm dim evening light from a bedside lamp, amber tones, vulnerable expression, messy hair, intimate atmosphere, film grain, shallow depth of field, photorealistic, 8k, --ar 1:1
```

### A3 — Токсичный
```
cinematic photorealism, medium shot of a tense man 35-40 years old in dark clothes, half-turned away from camera, looking over shoulder, harsh shadows across face, noir lighting, cold blue and black tones, aggressive posture, clenched jaw, urban apartment background at night, film noir aesthetic, contrasty, photorealistic, 8k, --ar 1:1
```

### A4 — Любящий
```
cinematic photorealism, medium shot of a warm man 30-35 years old in a soft cashmere sweater, reaching hand toward camera, gentle smile, golden hour sunset light streaming through window, warm orange and honey tones, crinkles around eyes, tender expression, cozy bedroom setting, film grain, soft focus, photorealistic, 8k, --ar 1:1
```

### B1 — Отдаление
```
cinematic photorealism, wide shot of a couple sitting on a modern sofa, both facing away from each other, large empty space between them, cold blue evening light from window, sad atmosphere, long shadows, modern minimalist apartment, emotional tension, film grain, photorealistic, 8k, --ar 1:1
```

### B2 — Протянутая рука
```
cinematic photorealism, over-the-shoulder shot, a man's hand reaching out toward a woman's back, she is turned away facing a window, soft warm light, bittersweet moment, tension between longing and distance, shallow depth of field, hand in focus, woman slightly blurred, photorealistic, 8k, --ar 1:1
```

### B3 — Прощание
```
cinematic photorealism, wide shot of a man silhouetted in a doorway, a woman sitting on the edge of the bed in the background, dim room with only bedside lamp on, heavy atmosphere, impending separation, film noir lighting, deep shadows, emotional weight, photorealistic, 8k, --ar 1:1
```

### C (Зинаида) — единый промпт для всех 5 портретов
```
portrait of ZINAIDA woman, 28 years old, long straight light brown hair, blue eyes, elegant white silk blouse, black and white photography, high contrast, dark background, Didone serif typography space at top 60% of frame, fashion editorial lighting, sharp focus on eyes, realistic skin texture with natural imperfections, half body shot, looking at camera, confident expression, photorealistic, editorial style, --ar 1:1
```
*Менять только выражение лица / эмоцию для C2-C5*

---

## БЮДЖЕТ ТЕСТА

| Направление | Модель | Кол-во | Цена | Итого |
|-------------|--------|--------|------|-------|
| A (мужчины) | FLUX Dev | 12 | $0.025 | $0.30 |
| B (пары) | FLUX Dev | 9 | $0.025 | $0.23 |
| C (Зинаида) | FLUX Dev + LoRA | 5 | $0.025 | $0.13 |
| **Итого** | | **26** | | **$0.66** |

Replicate ($5 бонус) — хватит на ~7 таких тестов. Тратим копейки.

---

## ЧТО ДАЛЬШЕ ПОСЛЕ ТЕСТА

Если Вариант 3 подтверждается:
1. Берём лучшие промпты как **шаблоны**
2. Контент-завод генерирует пост → выбирает типаж под тему → промпт в Леру → картинка готова за 3 минуты
3. Запускаем регулярное производство
4. Через неделю — смотрим метрики (saves, shares)
5. Итерация промптов под то что сработало

Если не заходит — возвращаемся к Варианту 1 (журнальная обложка) через Recraft V3.

---

*Файл вёл: Зинаида | Дата: 2026-07-10*
