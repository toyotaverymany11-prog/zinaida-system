# Визуальная дизайн-система карусели Instagram — 4 типа изображений

**Дата:** 2026-07-12 | **Для:** ниша психология отношений, ЦА женщины 18-40 РФ
**Полный гайд на сервере:** `/opt/zinaida/SmmFabrika/queue/Instagram/_carousel/CAROUSEL_GUIDE_2026.md`

---

## Единый визуальный язык

| Элемент | Значение |
|---------|----------|
| **Палитра** | Угольный #1A1A2E, графит #16213E, терракот #C05746, золото #D4A853, белый #FFFFFF |
| **Шрифт заголовков** | Didone Serif (PlayfairDisplay.ttf) — /opt/zinaida/SmmFabrika/assets/fonts/PlayfairDisplay.ttf |
| **Шрифт тела** | Чистый sans-serif |
| **Настроение** | Кинематографичное, «полуночный разговор», chiaroscuro |
| **Текстура** | Лёгкое зерно (как плёнка) |
| **Safe zone** | Центральные 1080×1080 из 1080×1350. Верх 120px + низ 150px — пусто |

---

## Тип A: Тёмный фон + типографика (3-7 слайдов)

**Роль:** Основной тип для контентных слайдов.

**Промпт (без текста):**
```
Dark abstract background, deep charcoal to midnight blue gradient, subtle grain texture, cinematic mood lighting, moody ambient atmosphere, no text, no people, minimalistic, 1080x1350
```

**Вариант с терракотовым акцентом:**
```
Dark background with warm terracotta #C05746 accent color, subtle gradient from charcoal to deep blue, cinematic side lighting, moody atmosphere, no text, no people, abstract minimalistic, 1080x1350
```

**Модель:** `fal-ai/gpt-image-2`

---

## Тип B: Силуэты / жесты / body language (2-3 слайда)

**Роль:** Эмоциональный удар. Без лиц — читательница проецирует себя.

**Силуэты двух людей спиной друг к другу:**
```
Blurred silhouettes of two people standing back to back in a dark room, dramatic side lighting from a window, cold blue tones, desaturated, distant atmosphere, emotional tension, photorealistic style, cinematic composition, no visible faces, shallow depth of field, 1080x1350
```

**Одинокая фигура:**
```
Blurred silhouette of a woman sitting alone on the edge of a bed in a dark room, cinematic lighting from side window, moody atmosphere, desaturated cool colors, shallow depth of field, photorealistic, emotional, lonely, 1080x1350
```

**Руки/жест:**
```
Close up of two hands reaching toward each other in dark space, dramatic spotlight, warm golden accent lighting, tension between reaching and pulling away, cinematic, photorealistic, emotional, shallow depth of field, 1080x1350
```

**Вариант: человек смотрит в телефон:**
```
Blurred silhouette of person sitting alone on a couch staring at phone screen, only light from phone illuminating face, dark room, cinematic, lonely atmosphere, blue screen light, emotional, 1080x1350
```

**Модель:** `fal-ai/gpt-image-2`

---

## Тип C: Предметы-метафоры (1-2 слайда)

**Роль:** Визуальная метафора для слайдов с цифрами и фактами.

**Разбитое стекло:**
```
Close up of cracked glass on dark surface, dramatic lighting from above, abstract metaphor for broken trust, sharp focus on crack lines, blurred background, cinematic dark mood, desaturated colors, 1080x1350
```

**Пустая комната:**
```
Empty dark room with scattered objects on floor, single light bulb hanging, dramatic shadows, cold desaturated colors, feeling of abandonment, cinematic composition, photorealistic, 1080x1350
```

**Зеркало/отражение:**
```
Large mirror in dark room with a blurred reflection, dramatic lighting, foggy atmosphere, metaphor for self-reflection, cinematic, moody, photorealistic, cool blue tones, 1080x1350
```

**Телефон:**
```
Smartphone lying face up on dark surface with blank dark screen, single warm spotlight, dramatic shadows, feeling of waiting for a message, cinematic, photorealistic, moody, 1080x1350
```

**Модель:** `fal-ai/gpt-image-2`

---

## Тип D: Зинаида (лицо) — 2-3 слайда

**Роль:** Узнаваемость бренда. Только на ключевых слайдах (1, 9, 10).

**Промпт:**
```
Portrait of zinaida, young woman 28 years old, serious confident expression, dark background, cinematic Rembrandt lighting, looking directly at camera, psychological analyst vibe, dark red lipstick, elegant, professional, high contrast, photorealistic, 1080x1350
```

**Вариант «взгляд в сторону» (для доверительного тона):**
```
Portrait of zinaida, young woman 28, three-quarter profile, thoughtful expression, soft side lighting, dark background, psychological analyst, elegant, professional, photorealistic, 1080x1350
```

**Модель:** `fal-ai/flux-lora` через FAL (trigger: zinaida, scale 0.6)

---

## Точные лимиты текста по слайдам

| Слайд | Роль | Символов | Слов | Тип |
|-------|------|----------|------|-----|
| 1 | Хук | **≤40** | 8-10 | D |
| 2 | Контекст | 150-250 | 25-40 | A |
| 3 | Цифра + факт | 100-200 | 15-30 | C |
| 4 | Вывод | 100-200 | 15-30 | B |
| 5 | Механика | 100-200 | 15-30 | A |
| 6 | «Что ты чувствуешь» | 100-200 | 15-30 | C |
| 7 | Пример | 100-200 | 15-30 | B |
| 8 | Разворот | 100-200 | 15-30 | A |
| 9 | Инструмент | 150-250 | 25-40 | D |
| 10 | CTA | **≤60** | 8-12 | A/D |

---

## 🚫 Запрещённые образы

- Стоковые фото «счастливых пар» (объятия на закате, свадьбы)
- Пастельные тона, розовый, голубой — «коуч-психолог» стиль
- Две половинки сердца, белые голуби, розы, свечи
- Улыбающиеся модели в светлых тонах
- «Ванильные» изображения, выглядящие как реклама
- Всё, что вызывает ассоциацию «глянцевый журнал о счастье»

## ✅ Что работает

- Психологический реализм — узнаваемые ситуации
- Эстетика «полуночного разговора» — темно, тихо, честно
- Кинематографичность — как кадр из фильма, не как реклама
- Драматическое освещение — chiaroscuro, боковой свет
- Без лиц на большинстве слайдов — для проекции
