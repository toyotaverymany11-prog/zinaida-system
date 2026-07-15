---
name: designer
description: "ГЛАВНЫЙ НАВЫК ДИЗАЙНА. Срабатывает когда первое слово в чате — дизайнер/дизайн/designer/design. Подтягивает ВСЁ: паспорт, FAL, Replicate, ошибки, скрипты, LoRA, VK обложки."
triggers:
  - "^дизайнер"
  - "^дизайн"
  - "^designer"
  - "^design"
related_skills:
  - copywriting/brand-font-zinaida
  - replicate-image-gen
  - apikey-image-gen
  - devops/zinaida-tech-protocol
---

# ДИЗАЙН-СЛОЙ ПРОЕКТА ОТНОШЕНИЯ

## ПРИ СТАРТЕ (первое слово = дизайнер/дизайн)

ОБЯЗАТЕЛЬНО:
1. Загрузить этот навык
2. Загрузить brand-font-zinaida (шрифт, цвета, VK обложки)
3. Загрузить replicate-image-gen (модели, API, питфоллы)
4. Показать актуальное состояние

ЗАПРЕЩЕНО:
- Выдумывать внешность Зинаиды — брать из паспорта 3.0 (блондинка)
- Использовать PIL/Pillow для текста на картинках
- Генерировать новое, если есть готовый результат
- Молчать про инструменты — показать FAL, Replicate, Pollinations
- **Говорить «показала/скинула» без реального файла/ссылки** — показать = отправить ИЗОБРАЖЕНИЕ, не описать словами
- **Использовать AI-генерации из `design/passport/generated/`** — там левые бабы, НЕ Зинаида
- **Отправлять картинку с лицом без сверки с референсами Зинаиды**

ФОРМАТ ДОСТАВКИ ОЛЕГУ (он на iPad):
- НЕ markdown `![alt](url)` — на iPad не даёт сохранить
- ✅ **Прямая текстовая ссылка** — просто URL строкой
- Если локальный файл — через MEDIA:путь

---

## 1. ПАСПОРТ ЗИНАИДЫ (v3.0, 12.07.2026)

**Файл:** `/opt/zinaida/design/passport/ZINAIDA_PASSPORT.md`

**⚠️ ВАЖНО: ПРАВИЛЬНЫЕ фото Зинаиды (подтверждено Олегом):**
- **Правильная папка (23 фото):** `/opt/zinaida/SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/`
  Файлы: zinaida_01.jpg ... zinaida_09_minimal.jpg, test_skin.jpg, zinaida_fullbody_*, zinaida_halfbody_*
- **Референсы (3 оригинала):** `/opt/zinaida/design/references/zinaida_face/` (IMG_9391.JPG, IMG_0413.PNG, IMG_0415.PNG)

**❌ НЕ ИСПОЛЬЗОВАТЬ (левые AI-генерации, не Зинаида):**
`/opt/zinaida/design/passport/generated/` — там front_serious, profile_left и т.д.

**Внешность (из реальных фото):**
- Волосы: **блонд/платиновый** (НЕ тёмные!)
- Глаза: голубые/голубовато-зелёные
- Возраст: 25-30
- Одежда: минимализм — чёрная водолазка, серый топ
- Сеттинг: студийный портрет

**Перед отправкой картинки с лицом — ОБЯЗАТЕЛЬНО сверить с референсами.**
Подробнее: `references/zinaida-photo-paths.md`

---

## 2. БРЕНД-АЙДЕНТИКА

| Элемент | Значение |
|---------|----------|
| Шрифт | Didone Serif (Playfair Display TTF: `/opt/zinaida/SmmFabrika/assets/fonts/PlayfairDisplay.ttf`) |
| Цвета | Чёрный #1A1A1A, бордовый #8B0000, золото #C9A84C, беж #F5E6D0 |
| Логотип | Небоскрёб + золотой «МЕГАМОЗГ» |
| Запрещено | Гротеск, Bebas Neue, Anton, sans-serif. PIL/Pillow для текста — НИКОГДА |

---

## 3. МОДЕЛИ ГЕНЕРАЦИИ

### FAL API: как генерировать через queue (проверено 12.07.2026)

**Синхронный режим (fal.run) — таймаутит на GPT Image 2.** Не использовать с --max-time меньше 120с.

**Асинхронный режим (queue.fal.run) — НАДЁЖНЫЙ СПОСОБ. Использовать его:**

```bash
# Шаг 1 — POST на queue.fal.run (возвращает request_id сразу)
curl -s -X POST https://queue.fal.run/fal-ai/gpt-image-2 \
  -H "Authorization: Key $FAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "...", "image_size": {"width": 1080, "height": 1350}}'

# Шаг 2 — Poll response_url, пока status не COMPLETED
curl -s "https://queue.fal.run/fal-ai/gpt-image-2/requests/<REQUEST_ID>" \
  -H "Authorization: Key $FAL_KEY"
# В ответе: {"images": [{"url": "..."}]} когда готово
# Пока не готово: {"detail": "Request is still in progress"}
```

**Идеограм V3 быстрее GPT Image 2:** ~5-8 секунд vs ~20-30 секунд для GPT Image 2. Если важна скорость — Ideogram. Если точность кириллицы — GPT Image 2.

**Важно:** `fal.run` (без queue) для GPT Image 2 тупо таймаутит через 60-90 секунд даже если генерация успешна. Всегда через queue.

**FAL_KEY:** `8e995491-ebb0-4650-8f66-dd0c2dee09ef:4fb8fc63694193ad8463f04ad9b25c1f` (из `/root/.hermes/.env`)
**Баланс:** $10 (пополнено 12.07.2026), одна генерация $0.04-0.06

### FAL.ai (ОСНОВНОЙ, $10 пополнено 12.07.2026)
- Конфиг: `provider: fal`, `model: fal-ai/flux-2/klein/9b` (дефолт $0.006)
- **Для кириллицы 🏆:** `fal-ai/gpt-image-2` ($0.04-0.06, 99% точность) — проверено, работает идеально
- **Для стиля «ЕГО СТРАХ»:** `fal-ai/ideogram/v3` ($0.03-0.09)
- **Для тестов:** `fal-ai/flux-2/klein/9b` ($0.006/MP)
- Все модели через встроенный `image_generate` tool Hermes

### Replicate API (⚠️ ТОЛЬКО РЕЗЕРВ, НЕ ИСПОЛЬЗОВАТЬ активно)

**Решение Олега от 12.07.2026:** Replicate НЕ ИСПОЛЬЗУЕМ. Только как резерв на крайний случай.

**LoRA Зинаиды на Replicate:** `toyotaverymany11-prog/zina` — существует, но не используем.

**Когда можно применить (только если FAL не работает):**
- Если FAL упал (баланс, ошибки) и нужно срочно сгенерировать лицо Зинаиды
- LoRA на FAL не справилась

### Pollinations.ai (БЕСПЛАТНО, без ключа)
- 768×768, нет кириллицы, нет LoRA

**Полный отчёт:** `/opt/zinaida/design/references/FAL_RESEARCH_REPORT.md`

---

## 4. ДИРЕКТОРИИ

| Директория | Что там |
|------------|---------|
| `/opt/zinaida/design/` | Весь дизайн |
| `/opt/zinaida/design/passport/` | Паспорт, generate_faces.py, 20+ фото |
| `/opt/zinaida/design/approved/` | Утверждённые: портреты, аватары, обложки |
| `/opt/zinaida/design/generated/` | Сгенерированные варианты |
| `/opt/zinaida/design/references/` | Референсы (лицо, стили, шрифты) |
| `/opt/zinaida/design/templates/` | Шаблоны промптов |
| `/opt/zinaida/dizayner/` | TASK_generate_remaining_faces |

---

## 5. FAL LoRA — ОБУЧЕНИЕ ЛИЦА ЗИНАИДЫ

**✅ ОБУЧЕНО 12.07.2026.** Trigger word: `zinaida`. Стоимость: $2.

### LoRA URL
```
https://v3b.fal.media/files/b/0aa1ef03/vcaC2BHukEixgZekjHkZL_pytorch_lora_weights.safetensors
```

### Использование
```python
import fal_client, os
os.environ['FAL_KEY'] = '...'

result = fal_client.subscribe('fal-ai/flux-lora', arguments={
    'prompt': 'portrait of a zinaida woman, blonde, blue eyes, black turtleneck, dark background',
    'loras': [{'path': lora_url, 'scale': 0.6}],
    'num_inference_steps': 30,
    'guidance_scale': 1.5,
    'image_size': 'square_hd'
})
```

### Реалистичное лицо — настройки (проверено 12.07.2026)

**Проблема:** FLUX + LoRA дают «пластиковое» лицо, кожа выглядит искусственно.

**Решение (3 версии, победила V3):**

| Параметр | V1 (❌ пластик) | V2 (⚠️ средне) | V3 (🏆 лучшая) |
|----------|----------------|----------------|----------------|
| LoRA scale | 1.0 | 0.85 | **0.6** |
| guidance_scale | 3.5 | 2.0 | **1.5** |
| steps | 28 | 30 | 30 |
| Negative prompt | нет | короткий | **агрессивный** |

**V3 промпт:**
```
Professional portrait photo of zinaida woman, 30 years old, blonde hair, blue eyes, 
natural makeup, black turtleneck, dark background. Real human skin texture, visible 
pores, fine wrinkles, natural imperfections, skin details, cinematic photography, 
sharp focus, depth of field
```

**V3 negative prompt:**
```
plastic, smooth, airbrushed, flawless, cgi, render, 3d, digital art, painting, 
illustration, fake skin, instagram filter, beauty filter, porcelain skin, wax skin, 
mannequin, doll, synthetic
```

**Вывод:** LoRA scale на FAL работает лучше при 0.5-0.7 (не 1.0). Guidance 1.5-2.0 даёт больше свободы модели.

Подробнее: `references/realistic-face-settings.md`

### Питфоллы
- Data URL в `images_data_url` слишком длинный — использовать `fal_client.upload_file()`
- `storage.fal.ai` не резолвится с сервера — не ходить напрямую
- FLUX не умеет кириллицу — текст через GPT Image 2 edit
- Правильные фото для датасета — только из `SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/`
- Не путать с `design/passport/generated/` — там AI-мусор

Подробнее: `references/fal-lora-training.md`

---

### 🏆 КЛЮЧЕВАЯ ТЕХНИКА 2026: TEXT-BEHIND-SUBJECT (стиль «ЕГО СТРАХ»)

**Суть:** текст сплетён с объектом в единую сцену. Часть букв ПЕРЕД объектом, часть ЗА ним. Не «наклейка сверху». Журнальная обложка Vogue-стиля.

**Полное досье:** `references/STYLE_EGO_STRAKH_DOSSIER.md`

**Два способа:**

**Способ А — Одним промптом (Ideogram V3 Turbo).** Для 2-3 слов. Промпт-шаблон:
```
A premium magazine cover. Giant bold headline "{ТЕКСТ}" in high-contrast
Didone serif font (like Bodoni / Didot): pure white letters, ~70% of frame.
A {ОБЪЕКТ} emerges from BETWEEN the giant letters: some letters IN FRONT,
the {ОБЪЕКТ} OVERLAPS other letters — interlocking by depth, NOT text on top.
Deep black background. One bordeaux (#8B0000) circle accent behind subject.
Dramatic side lighting. Minimalist Vogue aesthetic. Square 1:1.
CRITICAL: all text must be correct Russian Cyrillic.
```

**Способ Б — Композитинг.** FLUX → объект. Pillow → 3 слоя (фон → текст → объект). Кириллица 100%.

**Критическое правило:** перед любой генерацией обложки с кириллицей — загрузить `references/STYLE_EGO_STRAKH_DOSSIER.md` и сверить промпт с шаблоном.

---

### 🏆 Эталонные референсы

### 🏆 Референс №1: «ЕГО СТРАХ» (9.5/10)
- Модель: Ideogram V3 Turbo на Replicate (или `ideogram/v3` на FAL)
- Главный секрет: text-behind-subject (текст сплетён с объектом)
- Кириллица: ~90-95%
- Файл: `/opt/zinaida/design/references/STYLE_EGO_STRAKH.md`

### 🏆 Референс №2: «ЧУЖОЙ ЗАПАХ» (10/10) 🆕
- Модель: **GPT Image 2** на FAL (`fal-ai/gpt-image-2`)
- Кириллица: **99% точности**, много слов без единой ошибки
- Вывод: **ОСНОВНАЯ модель для обложек с русским текстом**
- Файл: `/opt/zinaida/design/references/STYLE_GPT_IMAGE_2.md`

---

## 6. КИРИЛЛИЦА НА КАРТИНКАХ — ПРОТОКОЛ

**Применяется ПЕРЕД любой генерацией с русским текстом.**

### Шаг 1 — Выбрать модель

| Ситуация | Модель | Сервис | Цена | Кириллица |
|----------|--------|--------|------|-----------|
| Обложка с текстом (2-3 слова) | Ideogram V3 | FAL `fal-ai/ideogram/v3` | $0.03-0.09 | ✅ 90-95% |
| **Много текста, точная кириллица** 🏆 | **GPT Image 2** | **FAL `fal-ai/gpt-image-2`** | **$0.04-0.06** | **✅ 99%** |
| Тест/черновик | FLUX 2 Klein | FAL `fal-ai/flux-2/klein/9b` | $0.006 | ❌ |
| Лицо Зинаиды | FLUX Dev + LoRA | Replicate | $0.025 | ❌ (текст не умеет) |

### Шаг 2 — Промпт-шаблон (Способ А)
```
A premium magazine cover. Giant bold headline "{ТЕКСТ}" in high-contrast
Didone serif font (like Bodoni / Didot): hairline thin serifs, heavy thick
vertical strokes, pure white letters, filling ~70% of the frame.
A {ОБЪЕКТ} emerges from BETWEEN the giant letters: some letters IN FRONT
of the {ОБЪЕКТ}, and the {ОБЪЕКТ} OVERLAPS other letters — interlocking
by depth, NOT text pasted on top.
Deep black background. One bordeaux (#8B0000) circle accent behind.
Dramatic side lighting. Minimalist luxury Vogue aesthetic. Square 1:1.
```

### Шаг 3 — Проверка (обязательно, см. п.7)

### Шаг 4 — Чек-лист приёмки
- [ ] Кириллица побуквенно правильно (нет лишних/потерянных букв)
- [ ] Шрифт Didone — тонкие засечки + жирные вертикали
- [ ] Текст сплетён с объектом — не наклейка сверху
- [ ] Ровно 3 цвета, один акцент (бордо #8B0000)
- [ ] Буквы ~70% кадра
- [ ] Драматический свет
- [ ] Формат 1:1 или 4:5
- [ ] Премиум, Vogue, дорого

**Если хоть один пункт «нет» → перегенерация или Способ Б.**

---

## 7. ПРОВЕРКА ТЕКСТА (ОБЯЗАТЕЛЬНО после каждой генерации)

### Уровень 1 — vision_analyze
Запрос: «Перечисли КАЖДУЮ букву на картинке по порядку. Каждая буква - кириллица или латиница? Сравни с ожидаемым [ТЕКСТ]. Напиши что реально написано.»

### Уровень 2 — Mistral Pixtral (если сомнения)
Модель: `pixtral-12b-2409` через Mistral API (бесплатно, у нас 4 ключа)
Запрос: «Read the Cyrillic text letter by letter. Check each character - is it proper Cyrillic or a Latin lookalike?»

### Правило:
- Если vision и Pixtral разошлись → текст скорее всего с ошибкой → перегенерация
- Ни Tesseract, ни EasyOCR не читают Didone шрифт — не полагаться на них

---

## 8. ПРОВЕРКА ЛИЦА — КРИТИЧЕСКОЕ ПРАВИЛО

**Перед отправкой Олегу ЛЮБОЙ картинки с лицом:**

1. Открыть `/opt/zinaida/design/references/zinaida_face/` (3 исходника)
2. vision_analyze с запросом: «Сравни лицо на этой картинке с референсными фото. Это та же женщина? Одинаковые черты лица, форма глаз, носа, губ? Или это левая баба?»
3. **Если не Зинаида — НЕ отправлять.** Перегенерировать с правильным подходом.

**Способы получить точное лицо Зинаиды (в порядке приоритета):**
1. **LoRA на FAL** (`fal-ai/flux-lora` + LoRA, trigger: zinaida, scale 0.6) — FLUX Dev
2. **Ideogram V3 Turbo** на Replicate — бесплатно, но без LoRA, только описание внешности
3. **GPT Image 2** на FAL — 99% кириллицы, без LoRA, только описание внешности
4. **Комбинированный подход:** FLUX LoRA → лицо Зинаиды. GPT Image 2 → текст. Собрать через композитинг (Pillow, Способ Б).

**⚠️ Предупреждение:** Олег моментально видит «левую бабу». Даже одна ошибка = сильный гнев.

**🚨 Критическая ошибка 12.07.2026 (ПОВТОР):** Дважды сгенерировала "левую бабу" вместо Зинаиды. Первый раз — GPT Image 2 с blonde hair. Второй — Ideogram V3 с dark hair. Оба раза не сверяла с референсами. **Перед любой отправкой картинки с лицом — СРАВНИТЬ с референсами.**

---

## 9. УДАЛЕНИЕ ВОДЯНЫХ ЗНАКОВ (inpainting)

Через GPT Image 2 edit endpoint на FAL:
```python
data_url = f'data:image/png;base64,{base64_encoded}'
# POST к fal.run/fal-ai/gpt-image-2/edit
# body: {"image_urls": [data_url], "prompt": "Remove watermark @BBOOT from top right corner...", ...}
```
Цена: $0.04-0.06. Проверить через vision что знак удалён.

---

## 10. ФОРМАТ ДОСТАВКИ КАРТИНОК ОЛЕГУ

**Олег на iPad. 12.07.2026: ССЫЛКИ НЕ НАЖИМАЮТСЯ. Картинки — напрямую в чат.**

### Что работает (по приоритету):

| Способ | Как делать | Когда |
|--------|-----------|-------|
| **🏆 vision_analyze** | `vision_analyze(image_url="/tmp/file.jpg")` — картинка в контекст | Показать результат генерации |
| **🏆 MEDIA:путь** | `MEDIA:/tmp/slide1.png` в тексте ответа | Файл на сервере |
| **🏆 send_message с MEDIA** | `send_message(message="MEDIA:/tmp/file.png")` | Отправить картинку в диалог |
| **URL текстом** | Строкой: `https://...` | Файл на стороннем сервере |

### 🚫 НЕ РАБОТАЕТ
- ❌ `![alt](url)` markdown — на iPad не даёт сохранить
- ❌ Описание словами вместо файла — «показала» ≠ описание

### 📌 ЖЁСТКОЕ ПРАВИЛО (12.07.2026)
Если Олег говорит **«скинь сюда», «отправь сюда»** — НЕ URL. Отправлять через vision_analyze или MEDIA.

**🚨 Ошибка 12.07.2026:** Сказала «показала две фотографии» — скинула URL. Олег не смог открыть.

---

## 11. ИСТОРИЯ ОШИБОК

1. **Паспорт врал** — тёмные волосы вместо блонда. Исправлено в v3.0.
2. **Докрутить ≠ сгенерировать новое** — 26 картинок вместо доработки 3 существующих
3. **PIL/Pillow для текста** — категорически запрещено Олегом
4. **Crop квадрата** для wide-формата — режет текст
5. **Serif на skyline** для VK обложек — «говно собачье»
6. **Recraft V3 врёт про кириллицу** — пишет латиницей
7. **Много итераций без результата** — 8+ попыток с тем же подходом
8. **Не сверять лицо с референсами Зинаиды** — отправлять левую бабу (повторялась дважды в этой сессии!)

**🚨 Критическая ошибка 12.07.2026:** Сказала «показала две фотографии» но не скинула их — только описала словами через vision_analyze. Олег: «ты сюда не скинула фотки блядь». Запомнить: **«показала» = отправить файл/ссылку, не описание.**

**🚨 Критическая ошибка 12.07.2026:** Перепутала папки с фото Зинаиды. Взяла AI-генерации из `design/passport/generated/` вместо правильных фото из `SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/`. Олег: «это не Зинаида, это хуйня полнейшая».

---

## 12. ЧТО НЕ ДОГЕНЕРИРОВАНО

15 ракурсов паспорта Зинаиды из 20 (готово 5). Файл: `TASK_generate_remaining_faces.md`
Нужно: Replicate LoRA + `generate_faces.py`
