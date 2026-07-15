# СТИЛЬ «ЕГО СТРАХ» — ПОЛНОЕ ДОСЬЕ
## Источник: дизайн-сессия 7-12 июля 2026
## Оценка Олега: 9.5/10

**Суть:** текст сплетён с объектом (text-behind-subject). Часть букв ПЕРЕД объектом, часть ЗА ним. Не «наклейка сверху».

---

### 🎨 ПАЛИТРА (неприкосновенна)
- Фон: глубокий чёрный #000000
- Текст: белый #FFFFFF
- Акцент: ОДИН бордовый круг #8B0000 за объектом
- Максимум 3 цвета

### 📐 КОМПОЗИЦИЯ
- Текст ~70% кадра, объект ~30%
- Буквы крупные, до краёв
- Объект вырастает из ПРОМЕЖУТКА между буквами
- Часть букв ПЕРЕД объектом, объект ПЕРЕКРЫВАЕТ часть букв
- ОДНА сцена, не «фото + подпись»

### 🔤 ШРИФТ
- Didone (Bodoni / Didot / Playfair Display)
- Тонкие засечки + жирные вертикальные штрихи
- Заглавные, очень крупные
- Только белый

### 💡 ОСВЕЩЕНИЕ
- Драматический боковой свет на объекте

### 📏 ФОРМАТ
- 1:1 (1080×1080) или 4:5 (1080×1350)

### 🤖 МОДЕЛЬ
- **Ideogram V3 Turbo** на Replicate (бесплатно)
- Либо Способ Б: композитинг (Pillow + FLUX Dev)

### 📝 ПРОМПТ-ШАБЛОН (Способ А)
```
A premium magazine cover. Giant bold headline "{ТЕКСТ}" in high-contrast
Didone serif font (like Bodoni / Didot): hairline thin serifs, heavy thick
vertical strokes, pure white letters, filling ~70% of the frame edge to edge.
A {ОБЪЕКТ} emerges from BETWEEN the giant letters: some letters IN FRONT
of the {ОБЪЕКТ}, and the {ОБЪЕКТ} OVERLAPS other letters — they are woven
together as one scene, interlocking by depth, NOT text pasted on top.
Deep black background. One bordeaux (#8B0000) circle accent behind the subject.
Dramatic side lighting. Minimalist luxury Vogue aesthetic. Square 1:1.
CRITICAL: all text must be correct Russian Cyrillic.
```

### 🚫 ПРАВИЛА КИРИЛЛИЦЫ (Способ А)
- Заголовок: 2-3 слова МАКС, ЗАГЛАВНЫМИ
- Простые слова: МОЛЧИТ, СТРАХ, УШЛА, ЗАПАХ
- Сложные ломаются → Способ Б (композитинг)
- Всегда проверять глазами через vision_analyze

### ✅ ЧЕК-ЛИСТ ПРИЁМКИ
- [ ] Кириллица побуквенно правильная
- [ ] Шрифт Didone (тонкие засечки + жирные вертикали)
- [ ] Текст сплетён с объектом (часть перед, часть за)
- [ ] Ровно 3 цвета, один акцент (бордо #8B0000)
- [ ] Буквы крупные, ~70% кадра
- [ ] Драматический свет
- [ ] Премиум, Vogue, дорого

### 🏆 УТВЕРЖДЁННЫЙ ПРОМПТ (7 июля 2026, v1_magazine_072725.png)
```
A premium magazine cover. Large bold text "ЕГО СТРАХ" in elegant high-contrast
Didone serif font, white color, thin serifs, bold vertical strokes, taking 70%
of the image area. Background: darkened photo of a confident elegant woman with
dark hair and auburn tips, wearing a white shirt, looking at camera with slight
smile. The woman is semi-transparent, background texture (30% opacity).
Dark gradient overlay from top. Black, white text, bordeaux (#8B0000) accent.
Vogue aesthetic. Professional typography. Clean minimalist layout.
```
