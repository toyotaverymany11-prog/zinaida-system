# 🏆 РЕФЕРЕНС №2: «ЧУЖОЙ ЗАПАХ» — GPT Image 2 (12.07.2026)

> **Дата создания:** 12.07.2026  
> **Оценка Олега:** 10/10 — «охуенный результат, супер»  
> **Сервис:** FAL.ai (встроен в Hermes)  
> **Модель:** `fal-ai/gpt-image-2`  
> **Цена:** $0.04-0.06/image  
> **Кириллица:** ✅ 99% точность — все слова правильные, много мелкого текста без ошибок  
> **Статус:** 🏆 ЭТАЛОН для кириллических обложек

---

## 📸 ИЗОБРАЖЕНИЕ

Ссылка: https://v3b.fal.media/files/b/0aa1ecd8/Df-tO3bJFUZDyPt3rA1eL_ruaSFEQJ.png

## ⚙️ ТЕХНИЧЕСКИЙ ПАСПОРТ

| Параметр | Значение |
|----------|----------|
| Сервис | FAL.ai |
| Модель | `fal-ai/gpt-image-2` |
| Промпт | См. ниже |
| Формат | 1:1 (square_hd) |
| Цена | $0.04-0.06/image |
| Качество | medium |
| Кириллица | ✅ идеально, много слов |

### Точный промпт:
```
A premium magazine cover. Large bold headline "ЧУЖОЙ ЗАПАХ" in high-contrast 
serif font, white color, taking 70% of the image area. A confident elegant woman 
with long straight blonde hair, light blue eyes, wearing a black turtleneck, 
emerges from between the letters. Deep black background. One bordeaux circle 
accent behind her. Dramatic side lighting. Minimalist luxury Vogue aesthetic. 
Square aspect ratio. CRITICAL: all text must be correct Russian Cyrillic.
```

---

## 💡 ОСОБЕННОСТИ

### Чем отличается от Ideogram V3:
- Кириллица 99% — буквально ВСЕ слова правильные, даже мелкие
- Умеет много текста (не только 2-3 слова, а целые слоганы)
- Не путает буквы (не пишет ЗЛАПАХ вместо ЗАПАХ)
- Стиль более «глянцевый», менее драматичный
- $0.04-0.06 против $0.03 у Ideogram V3

### Когда использовать:
- ✅ Для обложек с кириллицей — ОСНОВНАЯ МОДЕЛЬ
- ✅ Когда нужно много текста без ошибок
- ✅ Когда Ideogram V3 не справился с русским

### Когда НЕ использовать:
- ❌ Для LoRA лица Зинаиды (нужен Replicate FLUX Dev + LoRA)
- ❌ Когда нужен более драматичный/тёмный стиль (тут Ideogram V3)
- ❌ Для экономии ($0.04-0.06 дороже Klein $0.006)

---

## 📁 СВЯЗАННЫЕ ФАЙЛЫ

| Файл | Описание |
|------|----------|
| `/opt/zinaida/design/references/STYLE_GPT_IMAGE_2.md` | Этот файл |
| `/opt/zinaida/design/references/FAL_RESEARCH_REPORT.md` | Исследование FAL |

---

## 🔧 КОНФИГУРАЦИЯ HERMES

Для кириллических обложек:
```yaml
image_gen:
  provider: fal
  model: fal-ai/gpt-image-2   # ← переключать сюда для рус. текста
  use_gateway: false
```

Для обычных фоток/тестов:
```yaml
image_gen:
  model: fal-ai/flux-2/klein/9b  # ← для экономии, $0.006
```

*Архивировано 12.07.2026. Модель по умолчанию для кириллицы.*
