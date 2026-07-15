# ШАБЛОН ТЗ — Слайд 1 (Cover)
## Для Instagram карусели, стиль «ЕГО СТРАХ» / «ЦУКОЙ»

**Заполнить перед генерацией. НЕ импровизировать.**

---

### 1. СТИЛЬ (выбрать)
- [ ] **Трек 2: ЦУКОЙ/ЕГО СТРАХ** — чёрный фон, красный мазок, белый Didone, text-behind-subject
- [ ] Другой (указать): 

### 2. ТЕКСТ
| Позиция | Текст | Кол-во символов |
|---------|-------|-----------------|
| Крупно (как «ЦУКОЙ») | **[ЗАГОЛОВОК 1-3 слова]** | ≤ |
| Мелко внизу (опционально) | **[ПОДЗАГОЛОВОК]** | ≤ |

**Правила:** 
- Заголовок 2-3 слова ЗАГЛАВНЫМИ
- Простые слова (не длиннее 7 букв, не сложные термины)
- Если слово сложное — перейти на Способ Б (композитинг)

### 3. ОБЪЕКТ
- [ ] **Зинаида** (тёмные волосы, 28 лет, fair skin, серьёзная)
- [ ] Другое: 

**Описание для промпта:**
```
confident elegant young woman with dark hair, fair skin, dark eyes, serious
expression, [ОДЕЖДА: black turtleneck / white shirt], looking at camera
```

**🚫 НЕ писать:** blonde, blond, light hair, casual

### 4. ПАЛИТРА (ровно 3 цвета)
- Фон: #000000 (чёрный)
- Текст: #FFFFFF (белый)
- Акцент: #8B0000 (бордо) — круг/фигура за объектом

### 5. ТЕХНИКА
- [ ] **text-behind-subject** (часть букв ПЕРЕД объектом, часть ЗА). Не «наклейка сверху»
- [ ] Буквы ~70% кадра, от края до края
- [ ] Драматический боковой свет

### 6. МОДЕЛЬ
- [ ] `fal-ai/gpt-image-2` на FAL (99% кириллицы, $0.04-0.06)
- [ ] `ideogram-ai/ideogram-v3-turbo` на Replicate (бесплатно, 90-95%)
- [ ] FLUX + LoRA (только лицо, без текста)

### 7. ФОРМАТ
- [ ] 1:1 (1080×1080) — для профиля
- [ ] 4:5 (1080×1350) — для ленты

### 8. ПРОМПТ (собрать из шаблона)
```
A premium magazine cover. Giant bold headline "{ЗАГОЛОВОК}" in high-contrast
Didone serif font (like Bodoni / Didot): hairline thin serifs, heavy thick
vertical strokes, pure white letters, filling ~70% of the frame edge to edge.
A {ОПИСАНИЕ_ОБЪЕКТА} emerges from BETWEEN the giant letters: some letters are 
IN FRONT of the subject, and the subject OVERLAPS other letters — they are 
woven together as one scene, interlocking by depth, NOT text pasted on top.
Deep black background. One bordeaux (#8B0000) circle accent behind the subject.
Dramatic side lighting on the subject. Minimalist, clean, luxury Vogue
aesthetic, professional editorial typography. {ФОРМАТ: Square 1:1 / 4:5 portrait}.
CRITICAL: all text must be correct Russian Cyrillic.
```

### 9. ЧЕК-ЛИСТ ПРИЁМКИ (выполнить vision_analyze ПОСЛЕ генерации)
- [ ] Кириллица побуквенно правильная (НЕТ лишних/потерянных букв)
- [ ] Заголовок написан как указано (сравнить с п.2)
- [ ] Шрифт Didone (не обычный, не гротеск)
- [ ] Текст сплетён с объектом (часть перед, часть за) — НЕ наклейка
- [ ] Ровно 3 цвета (чёрный, белый, бордо)
- [ ] Буквы крупные, ~70% кадра
- [ ] Объект с тёмными волосами (НЕ блондинка)
- [ ] Премиум, Vogue, дорого
- [ ] Формат соответствует заданию (1:1 или 4:5)
- [ ] Нижние 150px / верхние 120px — без ключевой информации (для Instagram)

### 10. ДОСТАВКА ОЛЕГУ
1. Скачать локально: `curl -sL --max-time 15 "URL" -o /tmp/slideN.jpg` или `wget -q "URL" -O /tmp/slideN.jpg`
2. MEDIA:/tmp/slideN.jpg — только так, НЕ текстовой ссылкой
3. Не описывать словами что получилось — он увидит сам
