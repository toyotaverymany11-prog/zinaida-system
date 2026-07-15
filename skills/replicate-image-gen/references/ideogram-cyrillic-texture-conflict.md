# Ideogram Cyrillic + Texture Conflict — Case Study (10.07.2026)

## Задача
Сгенерировать обложку 1590×400px: текст "МЕГАМОЗГ" на тёмной мраморной поверхности.
Модель: `ideogram-ai/ideogram-v3-turbo`, aspect_ratio `3:1`.

## Попытки

### Попытка 1 — ❌ Кириллица искажена (выпадение букв)
**Промпт:** Акцент на мраморной текстуре + Didone шрифт + explicit letter spelling.
**Результат:** "МИОЗГ" вместо "МЕГАМОЗГ" — буквы "ЕГА" выпали. Мрамор был, текст испорчен.
**Вывод:** Текстура в промпте не защищает от выпадения букв.

### Попытка 2 — ✅ Кириллица корректна, ❌ фон плоский
**Промпт:** Убрал акцент на текстуру, усилил spelling: `"CRITICAL correct Cyrillic spelling: M then E then G then A then M then O then Z then G = МЕГАМОЗГ. Every letter perfectly legible."`
**Результат:** "МЕГАМОЗГ" корректно, но фон — чёрная текстура без мраморных прожилок.
**Вывод:** Усиление spelling решило кириллицу, но подавило текстуру.

### Попытка 3 — ✅✅✅ Всё корректно
**Промпт:** Вернул текстуру + negative: `"Typographic poster on polished dark marble stone background with visible white veins and natural stone texture. ... Realistic marble background, not solid black."` + explicit letter spelling.
**Результат:** "МЕГАМОЗГ" корректно + мраморные прожилки есть.
**Вывод:** Negative-конструкция `"not solid black"` помогла вернуть текстуру без потери текста.

## Ключевые инсайты
1. Ideogram может **выпадать буквы** (не только заменять) — это отдельный тип сбоя, не покрываемый explicit spelling
2. Text и texture **конкурируют** в промпте — их нужно настраивать итеративно
3. Negative в конце промпта (`"not solid black, not flat"`) помогает вернуть текстуру на 3-й попытке
4. Плановая стоимость: 3 генерации × $0.03 = $0.09 за рабочий результат
