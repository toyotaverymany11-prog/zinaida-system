---
name: replicate-image-gen
description: "Генерация изображений через Replicate API (FLUX, Recraft, Ideogram). Токен в REPLICATE_API_TOKEN."
version: 1.0.0
author: Zinaida-System
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [replicate, image-generation, flux, recraft, ideogram]
---

# Replicate Image Generation

**Решение от 12.07.2026:** Replicate переведён в резерв.
Основной провайдер — **FAL.ai** (через Hermes image_generate tool).
Replicate используется ТОЛЬКО если FAL упал. Подробнее: навык `designer`.

## Модели

### Текст-в-изображение
1. **FLUX Dev** (`black-forest-labs/flux-dev`) — $0.025/img — фотореализм
2. **Recraft V3** (`recraft-ai/recraft-v3`) — $0.04/img — дизайн, текст
3. **Ideogram V3** (`ideogram-ai/ideogram-v3`) — $0.08/img — текст на картинках
4. **Ideogram V3 Turbo** (`ideogram-ai/ideogram-v3-turbo`) — $0.03/img — дешёвый вариант с текстом

### Модель-специфичные параметры

#### Recraft V3 (`recraft-ai/recraft-v3`)
- **Поддерживаемые размеры (size):** строго из списка:
  `1024x1024`, `1365x1024`, `1024x1365`, `1536x1024`, `1024x1536`,
  `1820x1024`, `1024x1820`, `1024x2048`, `2048x1024`, `1434x1024`,
  `1024x1434`, `1024x1280`, `1280x1024`, `1024x1707`, `1707x1024`
- **Кастомный кроп:** если нужен размер вне списка (напр. 1590×400), выбери ближайший широкий (напр. 1820×1024) и обрежь центром через Pillow. **Важно:** если исходник меньше целевого размера по какой-то из осей — сначала ресайзни с сохранением пропорций (width-fit или height-fit, чтобы покрыть target), потом кропни центр:
  ```python
  from PIL import Image

  target = (1590, 400)
  w, h = img.size

  if w >= target[0] and h >= target[1]:
      # Source covers target — centre crop directly
      left = (w - target[0]) // 2
      top = (h - target[1]) // 2
      cropped = img.crop((left, top, left + target[0], top + target[1]))
  else:
      # Source smaller in one dimension — resize first to cover target
      # Pick the tightest fit ratio so the resized image covers the target
      ratio = max(target[0] / w, target[1] / h)
      new_size = (int(w * ratio), int(h * ratio))
      img_resized = img.resize(new_size, Image.LANCZOS)
      w2, h2 = img_resized.size
      left = (w2 - target[0]) // 2
      top = (h2 - target[1]) // 2
      cropped = img_resized.crop((left, top, left + target[0], top + target[1]))
  ```
- **Output format:** `jpg`, `png`, `webp`
- **Стоимость:** $0.04/img

#### FLUX Dev (`black-forest-labs/flux-dev`)
- **Параметры:** `guidance` (3.5), `num_inference_steps` (28), `width`/`height`
- **Стоимость:** $0.025/img

#### Ideogram V3 (`ideogram-ai/ideogram-v3`)
- **Стоимость:** $0.08/img
- **Параметры:**
  - `aspect_ratio`: строго из списка: `"1:1"`, `"3:1"`, `"1:3"`, `"1:2"`, `"2:1"`, `"9:16"`, `"16:9"`, `"10:16"`, `"16:10"`, `"2:3"`, `"3:2"`, `"3:4"`, `"4:3"`, `"4:5"`, `"5:4"`
  - **НЕ поддерживает** `CUSTOM` + width/height — только пресеты
  - Если нужен кастомный размер (напр. 1590×400), сгенерируй в ближайшем пресете (напр. `"3:1"` даёт 1536×512), затем обрежь/ресайзни через Pillow
  - `model`: `"V_3"` (по умолчанию) или `"V_3_TURBO"`
  - `output_format`: `"jpg"`, `"png"`, `"webp"`
  - `quality`: 1–100 (для jpg/webp)

- **Вывод (FileOutput):** `replicate.run()` для Ideogram возвращает `FileOutput` объект, НЕ строку/URL.
  ```python
  output = replicate.run("ideogram-ai/ideogram-v3-turbo", input={...})
  # output — FileOutput, не строка
  url = output.url  # правильный способ получить URL
  # или
  data = output.read()  # скачать bytes
  ```

- **Кириллица (важно):** Ideogram часто искажает кириллические буквы. Известны два типа сбоя:
  - **Подстановка/замена** (напр. "МЕГАМОЗГ" → "МЕСИВОЗТ") — буквы заменяются на похожие латинские или другие кириллические
  - **Выпадение букв** (напр. "МЕГАМОЗГ" → "МИОЗГ") — целые слоги пропадают. Это происходит даже при explicit letter-by-letter перечислении
  - **Конкуренция текст vs фон:** сильный акцент на правильности текста в промпте подавляет фоновые текстуры. Если нужна и корректная кириллица, и сложный фон (мрамор, кирпич, бетон) — они могут конфликтовать: одна генерация даёт правильный текст на плоском фоне, другая — текстуру с искажённым текстом

  Workaround (трёхэтапная итеративная стратегия):
  1. **Попытка 1** — полный промпт с текстом + текстурой + explicit letter spelling
  2. **Попытка 2** — если кириллица искажена, убрать акцент с текстуры, усилить spelling: `"CRITICAL correct Cyrillic spelling: М then Е then Г then А then М then О then З then Г = МЕГАМОЗГ. Every letter perfectly legible."` Если фон стал плоским — это ожидаемо, идём дальше
  3. **Попытка 3** — когда кириллица корректна, вернуть текстуру с явным negative: `"...Realistic [marble/brick/concrete] background, not solid black."` Если текстура появилась — ✅
  
  Ключевой принцип: **не пытайся исправить всё за одну генерацию**. Изолируй проблему — сначала добейся текста, потом текстуры.

  Дополнительные приёмы:
  - Добавить в промпт explicit перечисление букв: `"... every letter perfectly legible: М-Е-Г-А-М-О-З-Г..."`
  - Усилить акцент на правильности текста: `"...correct Russian Cyrillic spelling, all letters clearly readable..."`
  - Для возврата текстуры: `"...not solid black, not flat"` или `"...Realistic [material] background, not solid color"`
  - При необходимости регенерировать 2–3 раза (но с изменением промпта, не тот же самый)

#### Ideogram V3 Turbo (`ideogram-ai/ideogram-v3-turbo`)
- Всё то же самое, что Ideogram V3 (параметры, aspect_ratio, FileOutput, кириллица)
- **Стоимость:** $0.03/img (экономия vs V3)
- **Model parameter:** `"model": "V_3_TURBO"` (необязательно, авто-определяется по версии модели)

### Face-Reference (перенос лица на новый ракурс)
Для генерации консистентного лица персонажа в разных ракурсах используй модели, принимающие референсное изображение лица:

1. **IP-Adapter-Face-ID** (`fofr/ip-adapter-face-id`) — стабильная модель, принимает референс-фото лица + промпт. Не всегда доступна.
2. **SDXL IP-Adapter-Face-ID** (`fofr/sdxl-ip-adapter-face-id`) — версия на SDXL, лучшее качество. Не всегда доступна.
3. **Instant-ID** (`zsxkib/instant-id`) — **УДАЛЕНА (404)**, не пытаться. Альтернатива — IP-Adapter.
4. **TencentARC IP-Adapter FaceID Plus** (`tencentarc/ip-adapter-face-id-plusv2`) — ещё один вариант, бывает доступен.

**Типичный ввод для face-reference модели:**
```python
output = replicate.run("fofr/ip-adapter-face-id", input={
    "image": open("/path/to/reference_face.png", "rb"),  # референс лица
    "prompt": "portrait of a woman, 28 years old, serious look, professional photography, soft studio lighting",
    "num_outputs": 1,
    "width": 1024,
    "height": 1024,
    "negative_prompt": "cartoon, anime, distorted face, ugly"
})
```

**Важно:** face-reference модели на Replicate чувствительны к балансу аккаунта. При малом балансе — жёсткий рейт-лимит (~10 сек между запросами). Планируй генерацию серии с паузами, не пытайся запустить 10+ параллельно.

**Fallback:** Если face-reference модель недоступна (404, 429) — перейти на `apikey-image-gen` (Hermes Web UI → fun-codex).

## Быстрый старт

### FLUX Dev
```python
import replicate, os
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")
output = replicate.run("black-forest-labs/flux-dev", input={
    "prompt": "your prompt here",
    "guidance": 3.5,
    "num_inference_steps": 28,
    "width": 1024, "height": 1024,
    "output_format": "png"
})
```

### Ideogram V3 Turbo (with FileOutput handling + post-crop)
```python
import replicate, requests
from PIL import Image

output = replicate.run("ideogram-ai/ideogram-v3-turbo", input={
    "prompt": "Typographic poster. Russian word МЕГАМОЗГ in white serif...",
    "aspect_ratio": "3:1",  # только пресеты, не CUSTOM
    "model": "V_3_TURBO",
    "output_format": "jpg",
    "quality": 95,
})

# output — FileOutput, не строка
resp = requests.get(output.url, timeout=60)
resp.raise_for_status()
with open("result.jpg", "wb") as f:
    f.write(resp.content)

# Кастомный кроп, если нужен нестандартный размер
# ВАЖНО: при 3:1 → 1590×400 исходник (1536×512) уже target по ширине.
# Если исходник < target по какой-то оси — ресайзни с cover-fit, потом кропни.
img = Image.open("result.jpg")
target = (1590, 400)
w, h = img.size

if w >= target[0] and h >= target[1]:
    # Source covers target — centre crop directly
    left = (w - target[0]) // 2
    top = (h - target[1]) // 2
    cropped = img.crop((left, top, left + target[0], top + target[1]))
else:
    # Source smaller in one dimension — resize first (cover-fit), then crop
    ratio = max(target[0] / w, target[1] / h)
    img_resized = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    w2, h2 = img_resized.size
    left = (w2 - target[0]) // 2
    top = (h2 - target[1]) // 2
    cropped = img_resized.crop((left, top, left + target[0], top + target[1]))

cropped.save("cropped.jpg", quality=95)
```

## Реалистичная кожа
Добавляй к промптам портретов:
`Ultra-realistic skin with visible pores, natural imperfections, subsurface scattering`

## Known pitfalls

### 401 — Token expired
**Replicate API tokens expire and produce 401 errors.** The system does NOT auto-refresh — a human must replace `REPLICATE_API_TOKEN` in `.env`.

**Signs:**
```
requests.exceptions.HTTPError: 401 Client Error
```

**Resolution:**
1. Generate a new token at https://replicate.com/account/api-tokens
2. Update `.env`: `REPLICATE_API_TOKEN=<new_token>`
3. If no token is available, **fall back to apikey-image-gen** (Hermes Web UI → fun-codex provider)

### 429 — Rate limited (low balance or burst limit)
**Типы 429 ошибок:**

**А. Rate-limit при низком балансе (< $5)** — временное ограничение, НЕ тупик.
Симптомы:
```
replicate.exceptions.ReplicateError: 429 Too Many Requests
detail: ...rate limit ... reduced to 6 requests per minute with a burst of 1 ... resets in ~5s
```
**Важно:** `burst of 1` означает, что единовременно выполняться может только 1 запрос
от ВСЕХ источников (агентов, кронов, ручных вызовов). Если кто-то ещё шлёт запросы,
твой слот может быть занят — и ожидание N+5 не поможет.

**Решение (пошагово):**
1. Прочитать `resets in ~Ns` из сообщения — это минимальный backoff.
2. Если в системе есть другие активные агенты или кроны, шлющие запросы на Replicate,
простое N+5 может не сработать — слот забирает другой процесс между retry.
3. **Практическое правило:** при `burst of 1` ставь таймаут **30–60 секунд**, а не N+5.
Если через 30с всё ещё 429 → подожди ещё 30с. Повторная попытка почти всегда работает,
если дать достаточно времени, чтобы другие процессы освободили слот.
4. После 3+ неудачных попыток подряд → перейти к fallback на `apikey-image-gen`.

Не переключайся на fallback сразу — это не dead end, а вопрос терпения.

**Б. Budget exhausted / No credits** — тупик.
**Решение:** fallback на `apikey-image-gen` (Hermes Web UI → fun-codex).

### Face-Reference generation — face consistency problem
IP-Adapter и Instant-ID **не гарантируют** консистентность черт лица между разными генерациями. Даже с одним референсом, в разных ракурсах могут получиться разные глаза/нос. Для настоящей консистентности нужен LoRA (fine-tune) или ручной отбор лучших кадров.

### Fallback strategy
When Replicate fails:
- **401 (token expired):** не retry, сразу fallback
- **429 (rate-limit, сообщение «resets in ~Ns»):** подожди 30–60 секунд (burst=1 может забрать слот), retry — обычно работает. После 3+ неудач — fallback.
- **429 (budget exhausted):** не retry, сразу fallback
- **404 (model removed):** не retry, попробуй другую модель или fallback

**Face-reference specific fallback:** когда face-reference модель на Replicate недоступна (404, 429), а задача требует консистентного лица — apikey-image-gen может не справиться с переносом лица. В этом случае:
- Попробовать другую face-reference модель из списка выше
- Сократить количество ракурсов и увеличить задержку между запросами (10+ сек)
- Если всё упало — сообщить оператору: нужен новый Replicate-токен или альтернатива

## Бюджет
$10 = ~400 генераций FLUX Dev, или ~250 Recraft V3, или ~330 Ideogram V3 Turbo

## Hermes image_gen plugin (обёртка, с 10.07.2026)

**Путь:** `/root/.hermes/plugins/image_gen/replicate/`

Это ImageGenProvider-обёртка, которая подключает Replicate API к стандартному тулу Hermes `image_generate`. Команда «сгенерируй картинку» → Hermes сам идёт через плагин в Replicate, ждёт, скачивает. Не нужно вручную дёргать терминал.

**Конфиг в `/root/.hermes/config.yaml`:**
```yaml
image_gen:
  provider: replicate
  model: flux-dev
```

### Когда плагин, а когда ручной API
| Ситуация | Плагин | Ручной API |
|----------|--------|------------|
| Простая генерация, портреты | ✅ | ❌ излишне |
| **LoRA** (ZINAIDA trigger_word) | ❌ НЕ УМЕЕТ | ✅ обязательно |
| Face-Reference (IP-Adapter) | ✅ с reference_image | ✅ полный контроль |
| Кастомные параметры (guidance, steps) | ❌ | ✅ |
| Кириллица (Ideogram) | ✅ model=ideogram-v3 | ✅ |

### 9 моделей в плагине
`flux-dev` ($0.025, основная), `flux-schnell` ($0.003, быстрая), `flux-1.1-pro` ($0.05, премиум), `recraft-v3` ($0.04, дизайн/текст), `ideogram-v3` ($0.08, кириллица), `ideogram-v3-turbo` ($0.03, кириллица дёшево), `ip-adapter-face-id` (~$0.01, перенос лица), `sdxl-ip-adapter-face-id` (~$0.01), `ip-adapter-faceid-plusv2` (~$0.01).

### Питфоллы при написании image_gen плагинов
1. `error_response(error="текст", ...)` — ТОЛЬКО keyword-only, не позиционные
2. `success_response(image=путь, ...)` — аргумент `image`, не `image_path`
3. Плагины кэшируются Gateway — после правки: `pkill -9 -f hermes-gateway`, очистка `__pycache__`, рестарт
4. Hermes Studio кэширует через bridge-worker — может нужен /reset

### Reference files
- `references/hermes-image-gen-plugin.md` — архитектура плагина (см. отдельный файл)
- `references/alternative-image-gen-providers.md` — карта всех способов генерации

## Связанные навыки
- `apikey-image-gen` — основной fallback при отказе Replicate
- `zinaida-operations` — LoRA fine-tuning, face consistency

## Reference files
- `references/alternative-image-gen-providers.md` — карта всех способов генерации изображений: FAL.ai, Pollinations.ai, HuggingFace, Hermes Plugin System
- `references/hermes-image-gen-plugin.md` — архитектура Hermes image_gen плагина для Replicate (см. отдельный файл)
- `templates/pollinations-image-gen-plugin.py` — рабочий шаблон image_gen провайдера для Hermes
- `references/zinaida-lera-workflow.md` — workflow агента Леры
