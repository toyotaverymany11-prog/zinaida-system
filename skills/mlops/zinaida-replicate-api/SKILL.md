---
name: zinaida-replicate-api
description: "Правильный способ вызова Replicate API: FLUX LoRA, Nano Banana 2, Seedream, Ideogram. Прямые HTTP запросы, выбор модели под задачу, кириллица на картинках. Модельный парк контент-завода Зинаиды."
---

# Replicate API для контент-завода Зинаиды

## ПРОБЛЕМА: replicate Python библиотека сломана
Replicate Python библиотека (`replicate.run()`) возвращает `FileOutput` объект для моделей типа FLUX.
Ошибка: `'FileOutput' object has no attribute 'type'`.
**Решение: использовать прямые HTTP запросы, не библиотеку.**

## Правильный способ: прямые HTTP запросы

### 1. Создание prediction (POST + poll)
```python
import json, urllib.request, time

TOKEN=***  # из /opt/zinaida/config/secrets.env
MODEL = "toyotaverymany11-prog/zina:8ecf86f0e06fd867e2a675d7b9086d9ffc5e5d88cb1882d67da36476c4486638"

payload = json.dumps({
    "input": {
        "prompt": "ZINAIDA, raw portrait photo, ...",
        "guidance_scale": 2.5,
        "num_inference_steps": 30
    }
}).encode()

req = urllib.request.Request(
    f"https://api.replicate.com/v1/models/{MODEL}/predictions",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
)
resp = urllib.request.urlopen(req, timeout=30)
pred_id = json.loads(resp.read())["id"]
```

### 2. Poll до готовности
```python
for attempt in range(60):
    time.sleep(5)
    req = urllib.request.Request(
        f"https://api.replicate.com/v1/predictions/{pred_id}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    data = json.loads(urllib.request.urlopen(req).read())
    status = data.get("status")
    
    if status == "succeeded":
        url = data.get("output")
        if isinstance(url, list):
            url = url[0]
        break
    elif status == "failed":
        raise Exception(data.get("error"))
```

### 3. Rate Limits
- **Лимит:** ~6 predictions в минуту на аккаунт
- **Между запросами:** минимум 10 секунд паузы
- **429 ошибка:** ждать 60 секунд и повторить
- **Batch генерация:** делать последовательно, не параллельно

### 4. Скачивание результата
```python
with urllib.request.urlopen(url) as img:
    with open("output.jpg", "wb") as f:
        f.write(img.read())
```

### 5. Чтение токена (правильно)
```python
tok = ''
with open('/opt/zinaida/config/secrets.env') as f:
    for line in f:
        if 'REPLICATE_API_TOKEN' in line:
            tok = line.strip().split('=', 1)[1]
            break
```
**ВАЖНО:** Не копировать токен из вывода терминала, Hermes маскирует его как `***`.
Всегда читать из файла.

### 6. Не использовать Prefer wait header
`Prefer: wait` заставляет API ждать до 60 секунд, но часто возвращает null output.
Лучше: создать prediction без `Prefer: wait`, получить ID, потом poll.

## Модели для кириллицы (текст на картинке)

Для контент-завода Зинаиды критична кириллица на изображениях.
Большинство диффузионных моделей (FLUX, SD3) не умеют русский текст.
Использовать специализированные модели.

### Nano Banana 2 (google/nano-banana-2) — 🏆 ЛУЧШАЯ ДЛЯ КИРИЛЛИЦЫ
| Параметр | Значение |
|----------|----------|
| **ID** | `google/nano-banana-2` |
| **Цена** | $0.035/шт |
| **Скорость** | **5 секунд** (самая быстрая) |
| **Кириллица** | ✅ Идеальная, буква Г не путается с G |
| **Лицо Зинаиды** | ❌ Не копирует 1:1 (не использовать для портретов) |
| **Стиль** | Фотореализм, cityscape, архитектура |

**⚠️ КРИТИЧЕСКИЙ ПИТФОЛЛ: width/height ИГНОРИРУЮТСЯ**
Модель ВСЕГДА возвращает **1024×1024**, независимо от переданных width/height.
Это особенность Replicate-обёртки Nano Banana 2.
**Решение:** всегда генерировать в 1024×1024, потом обрезать/ресайзить до нужного формата через Pillow (техоперация, не творческий дизайн).

**Когда использовать:** текст на картинке (вывески, билборды, заголовки), городские пейзажи, архитектурные сцены, scenes без портрета человека.

**Когда НЕ использовать:** портреты Зинаиды (брать FLUX Dev + LoRA toyotaverymany11-prog/zina).

**⚠️ КРИТИЧЕСКИЙ ПИТФОЛЛ: serif на skyline = ГОВНО (подтверждено Олегом 10.07.2026)**
Промпт с serif шрифтом на ночном небоскрёбе (типа «golden serif letters МЕГАМОЗГ как architectural landmark sign») — категорически НЕ ИСПОЛЬЗОВАТЬ.
Олег назвал результат «говно собачье». Правильный стиль: небоскрёб снят снизу вверх (low angle), текст на крыше/верхушке здания, не serif, а жирный современный шрифт (sans-serif). См. референс `vk_cover_arch.jpg` в `/opt/zinaida/design/approved/`.

**Проверенный промпт для VK обложки (стиль, утверждённый Олегом 10.07.2026):**
```python
prompt = """Night view of a tall skyscraper, dramatic low angle from street level looking up, 
large golden glowing Cyrillic letters saying МЕГАМОЗГ in Russian at the top of the building 
as illuminated rooftop sign, below it in smaller white Cyrillic letters читаю мужиков как код, 
even smaller gray text AI психоаналитик, dark sky, city lights, photorealistic, cinematic"""
```

### Ideogram V3 Turbo (ideogram-ai/ideogram-v3-turbo) — ✅ ДЛЯ ЖУРНАЛЬНЫХ ОБЛОЖЕК

| Параметр | Значение |
|----------|----------|
| **Цена** | $0.03/шт (бесплатно на старом аккаунте) |
| **Скорость** | 5-10 секунд |
| **Кириллица** | ⚠️ 90-95%, иногда путает буквы. Простые слова (2-3) работают |
| **Стиль** | 🏆 Промпт-шаблон text-behind-subject (см. ниже) |
| **Проверено** | 7 июля 2026 — «ЕГО СТРАХ» 9.5/10. 12 июля 2026 — «ЧУЖОЙ ЗАПАХ» (ошибки) |

**Промпт-шаблон для журнальной обложки (text-behind-subject):**
```
A premium magazine cover. Giant bold headline "{ТЕКСТ}" in high-contrast
Didone serif font (like Bodoni / Didot): hairline thin serifs, heavy thick
vertical strokes, pure white letters, filling ~70% of the frame edge to edge.
A {ОБЪЕКТ} emerges from BETWEEN the giant letters: some letters IN FRONT
of the {ОБЪЕКТ}, and the {ОБЪЕКТ} OVERLAPS other letters — interlocking
by depth, NOT text pasted on top. Deep black background.
One bordeaux (#8B0000) circle accent behind the subject.
Dramatic side lighting. Minimalist luxury Vogue aesthetic. Square 1:1.
CRITICAL: all text must be correct Russian Cyrillic.
```

**Когда использовать:** журнальные обложки, magazine-style, text-behind-subject.
**Когда НЕ использовать:** много текста (более 3 слов) — Ideogram ломает буквы.

**Для многословной кириллицы → GPT Image 2 на FAL (99% точности).**

### Seedream 5.0 Lite (bytedance/seedream-5-lite)
| Параметр | Значение |
|----------|----------|
| **Цена** | $0.03/шт |
| **Скорость** | 6-10 секунд |
| **aspect_ratio** | ✅ Поддерживает '3:1' → 1536×512 нативно |
| **magic_prompt_option** | 'Auto' (строго с большой A) |
| **Кириллица** | ⚠️ 90-95%, иногда путает буквы |
| **Профиль** | 🏆 Основной для VK обложек (wide-формат без crop) |

### Seedream 5.0 Lite (bytedance/seedream-5-lite)
| Параметр | Значение |
|----------|----------|
| **Цена** | $0.035/шт |
| **Кириллица** | ✅ Отличная (текст в двойных кавычках) |
| **Reference** | Поддерживает до 14 reference images |
| **Профиль** | Перспективная модель, если нужно лицо + текст (через несколько reference) |

### Выбор модели под задачу

| Задача | Модель | Почему |
|--------|--------|--------|
| Текст на вывеске/билборде/архитектуре (квадрат) | Nano Banana 2 | Лучшая кириллица, 5 сек |
| **VK обложка 1590×400 (wide-формат)** | **Ideogram V3 Turbo** | **aspect_ratio='3:1' → 1536×512, без crop** |
| Портрет Зинаиды | FLUX Dev + LoRA ZINAIDA | Идеальное лицо |
| Портрет + текст гибрид | FLUX Dev + LoRA → FLUX Fill | Лицо ✅, текст через inpainting |
| Журнальная обложка с текстом | Recraft V3 (повторный тест) | Теоретически лучшая, на практике требует уточнения промпта |
| Черновик / быстрый тест | FLUX Schnell ($0.003) | Самый дешёвый |

## FAL.ai — альтернативный провайдер (добавлен 10.07.2026)

Hermes Agent поддерживает **FAL.ai** из коробки через тул `image_generate`.
Это альтернатива Replicate для случаев, когда Nano Banana 2 не даёт нужного формата.

**Когда использовать FAL вместо Replicate:**
- Нужен нативный wide-формат (не квадрат 1024×1024)
- Нужно быстро, без скриптов и polling
- Нужен FLUX за $0.006/MP (в 4 раза дешевле Replicate)
- GPT Image 2 для кириллицы (SOTA text rendering + CJK)

**Когда НЕ использовать FAL (только Replicate):**
- Портреты Зинаиды (нужна LoRA toyotaverymany11-prog/zina — только на Replicate)
- Генерации с кастомными LoRA

**Модели FAL для кириллицы:**
| Модель | ID | Цена | Скорость |
|--------|----|------|----------|
| GPT Image 2 | `fal-ai/gpt-image-2` | $0.04-0.06 | ~20 сек |
| Nano Banana Pro | `fal-ai/nano-banana-pro` | $0.15/image | ~8 сек |
| Ideogram V3 | `fal-ai/ideogram/v3` | $0.03-0.09 | ~5 сек |
| FLUX 2 Klein | `fal-ai/flux-2/klein/9b` | $0.006/MP | <1 сек |

**Настройка:** `FAL_KEY` в `.env` → `image_gen.enabled: true` в config.yaml.
Подробнее: навык `brand-font-zinaida/references/fal-ai-integration.md`.

**Ключевое отличие от Replicate:** FAL поддерживает `image_size` и `aspect_ratio` —
не нужно мучиться с crop квадрата. Для VK обложки: `image_size: landscape_16_9`.

---

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `FileOutput object has no attribute type` | Используется replicate.run() | Заменить на HTTP запросы |
| `429 Too Many Requests` | Превышен rate limit | Пауза 10-60 сек |
| `output: None` | Prediction не готов | Использовать polling |
| `401 Unauthorized` | Неверный токен | Читать из secrets.env |

## GitHub Models vision
- **Endpoint:** `https://models.github.ai/inference/chat/completions`
- **Модель:** `gpt-4o-mini` (бесплатно ~150/день)
- **Требуется:** GitHub PAT со scope models:read
- **Формат:** OpenAI-совместимый (content с image_url)

## Mistral API (альтернатива)
- **Endpoint:** `https://api.mistral.ai/v1/chat/completions`
- **Текст:** `mistral-large-latest` (быстрая, русский хороший, ~1.1 сек)
- **Vision:** `mistral-large-latest` сам видит картинки (image_url в content)
- **Важно:** Mistral использует brotli-сжатие. **Обязательно** передавать `Accept-Encoding: identity` или `deflate, gzip` иначе ошибка `Can not decode content-encoding: br`
- **Pixtral:** не существует (ошибка invalid model)
- **Multi-key:** 2 ключа в .env (MISTRAL_API_KEY, MISTRAL_API_KEY_2). Ротация: если лимит ключа 1 исчерпан → автоматом ключ 2
- **Скорость:** текст ~1-2 сек, vision ~10-18 сек
- **Добавление ключей:** Писать в `/opt/zinaida/.env` и `/opt/zinaida/config/secrets.env` через python heredoc (echo с маскировкой ломает токены)

## Vision Proxy (GitHub → Mistral → Ollama fallback)
**Скрипт:** `/opt/zinaida/scripts/vision_fallback_proxy.py` порт 8901
systemd: `vision-proxy.service`
1. GitHub Models (gpt-4o-mini) — быстрый (~10 сек), бесплатный
2. Mistral (mistral-large-latest) — самый детальный (~18 сек), если GitHub не ответил
3. Ollama Cloud (gemma3:27b, 3 ключа, авто-сжатие PNG→JPEG) — резерв

**Прокси сам сжимает большие PNG (1024px, JPEG 80%)** — не надо сжимать перед отправкой.
**Health:** `curl http://127.0.0.1:8901/health` — показывает github/mistral/ollama_keys статусы.
**Mistral brotli fix:** в коде прокси используется `Accept-Encoding: identity` для Mistral запросов.

**Hermes config:**
```yaml
vision:
  provider: ollama
  model: gemma3:27b
  base_url: http://127.0.0.1:8901
  api_key: proxy
  timeout: 120
```
Подробнее: `references/vision-proxy.md`

## GigaChat API (Сбер)
- OAuth: ключ → POST ngw.devices.sberbank.ru → token 30 мин (expires_at в ms)
- Бесплатно: только текст (GigaChat, не GigaChat-Max!)
- Vision: GigaChat-2-Max платный (402 Payment Required на бесплатном тарифе)
- verify_ssl_certs=False (самоподписанные сертификаты)
- Python SDK: `pip install gigachat` — но SDK не поддерживает vision (content должен быть строкой, не списком)
- Через прямой API: загрузить файл → получить file_id → передать в `attachments` параметр сообщения
- Документация: `/opt/zinaida/inbox/GigaChat_API.md`

### 7. Hermes image_gen plugin для Replicate (добавлено 2026-07-10)

Написан Hermes image_gen плагин, подключающий Replicate к встроенному `image_generate` тулу.
Команда «сгенерируй» → Hermes сам идёт через плагин в Replicate.

**⚠️ ДЕРЕВО РЕШЕНИЙ — какой способ использовать:**

```
┌─ Нужна картинка?
│
├─ Нужна LoRA (лицо Зинаиды, trigger ZINAIDA)?
│  └─→ Ручной API через terminal (раздел 1-5 этого навыка)
│
├─ Нужны кастомные параметры (guidance, steps, negative_prompt)?
│  └─→ Ручной API через terminal
│
├─ Batch-генерация (несколько картинок)?
│  └─→ Ручной API через terminal (последовательно, rate limit 6/мин)
│
└─ Простая картинка (пейзаж, объект, текст, архитектура)?
   └─→ image_generate tool → Replicate plugin автоматом
```

**Ключевое правило:** при старте дизайн-сессии сначала пробовать `image_generate`.
Он быстрее (6-10 сек), не требует urllib кода, сам ждёт результат.
Ручной API — только для LoRA и кастомных параметров.

**Плагин:** `/root/.hermes/plugins/image_gen/replicate/`
**Конфиг:** `image_gen.provider: replicate, model: flux-dev` в `/root/.hermes/config.yaml`
**Токен:** REPLICATE_API_TOKEN из `.env` (подхватывается автоматически)

**9 моделей в плагине:**
| Модель | owner/name | Цена |
|--------|-----------|------|
| `flux-dev` | black-forest-labs/flux-dev | $0.025 |
| `flux-schnell` | black-forest-labs/flux-schnell | $0.003 |
| `flux-1.1-pro` | black-forest-labs/flux-1.1-pro | $0.05 |
| `recraft-v3` | recraft-ai/recraft-v3 | $0.04 |
| `ideogram-v3` | ideogram-ai/ideogram-v3 | $0.08 |
| `ideogram-v3-turbo` | ideogram-ai/ideogram-v3-turbo | $0.03 |
| `ip-adapter-face-id` | fofr/ip-adapter-face-id | ~$0.01 |
| `sdxl-ip-adapter-face-id` | fofr/sdxl-ip-adapter-face-id | ~$0.01 |
| `ip-adapter-faceid-plusv2` | tencentarc/ip-adapter-face-id-plusv2 | ~$0.01 |

**Когда НЕ использовать плагин (только ручной API через replicate-image-gen навык):**
- LoRA (ZINAIDA trigger_word) — плагин не умеет
- Кастомные параметры (guidance, num_inference_steps, negative_prompt)
- Batch-генерация нескольких картинок

**Архитектура плагина:**
```
/root/.hermes/plugins/image_gen/replicate/
├── __init__.py    # ImageGenProvider наследник + register(ctx), ~300 строк
└── plugin.yaml    # kind: backend, name: replicate
```

**Критический API контракт (keyword-only):**
```python
from agent.image_gen_provider import error_response, success_response

# ТОЛЬКО keyword arguments!
return error_response(error="текст", provider="replicate", prompt=prompt)
return success_response(image="/path/img.jpg", model="flux-dev",
                        prompt=prompt, aspect_ratio="square", provider="replicate")
```
- error_response() и success_response() не принимают позиционных аргументов
- Параметр image (не image_path!)
- Все поля строго keyword-only. При нарушении: TypeError.

**Поддерживаемые aspect_ratio для FLUX в плагине (добавлены 10.07.2026):**
| Формат | Назначение | Размер (wxh) |
|--------|-----------|-------------|
| 1:1 | Пост квадрат | 1024×1024 |
| 16:9 | Landscape | 1344×768 |
| 9:16 | Portrait | 768×1344 |
| **3:1** | **VK обложка** | **1536×512** |
| **4:1** | **Альтернатива VK** | **1600×400** |
| **2:1** | **Широкий формат** | **1408×704** |
| 3:2 | Фото 3:2 | 1216×832 |
| 4:3 | Фото 4:3 | 1152×896 |

**ВАЖНО:** Эти размеры работают ТОЛЬКО через `image_generate` тул Hermes (плагин).
При прямом API вызове через terminal всё равно игнорируются (FLUX использует `aspect_ratio` строкой).
Плагин же конвертирует aspect_ratio → width/height для FLUX.

**Плагины кэшируются Gateway:** после изменений полная перезагрузка:
```bash
pkill -9 -f hermes-gateway
rm -rf /root/.hermes/plugins/image_gen/*/__pycache__
cd /usr/local/lib/hermes-agent && npx hermes gateway start --daemon
```
Hermes Studio может требовать /reset сессии из-за bridge-worker кэша.

**Переключение между провайдерами:**
```yaml
# В /root/.hermes/config.yaml
image_gen:
  provider: replicate   # или pollinations (бесплатно)
  model: flux-dev       # модель по умолчанию
```

**FAL fallback trap:** Если плагин не зарегистрируется, а FAL_KEY есть в окружении — Hermes тихо переключится на FAL. FAL при exhausted balance падает с `error_response(...)`. Диагностика:
```python
from hermes_cli.plugins import _ensure_plugins_discovered
from agent.image_gen_registry import get_active_provider, list_providers
_ensure_plugins_discovered(force=True)
print(get_active_provider().name)  # replicate / pollinations / fal
```

## HuggingFace Inference API (бесплатно, добавлено 2026-07-10)

**Сайт:** https://huggingface.co/
**Регистрация:** https://huggingface.co/join
**Токен:** https://huggingface.co/settings/tokens

**НОВЫЙ API эндпоинт (2025-2026):**
Старый `api-inference.huggingface.co` — больше не работает (DNS не резолвится).
Новый: `router.hunggingface.co/hf-inference/models/{model_id}`

```bash
curl -X POST "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell" \
  -H "Authorization: Bearer hf_ТОКЕН" \
  -H "Content-Type: application/json" \
  -d '{"inputs":"промпт"}'
```

**Доступные модели (бесплатно, с токеном):**
| Модель | ID | Скачиваний |
|--------|-----|------------|
| FLUX.1-schnell | black-forest-labs/FLUX.1-schnell | 242k |
| FLUX.1-dev | black-forest-labs/FLUX.1-dev | 625k |
| SDXL | stabilityai/stable-diffusion-xl-base-1.0 | 1.4M |
| SD 3.5 Medium | stabilityai/stable-diffusion-3.5-medium | 615k |
| SDXL Turbo | stabilityai/sdxl-turbo | 750k |
| Realistic Vision V5.1 | SG161222/Realistic_Vision_V5.1_noVAE | 516k |
| Z-Image Turbo | Tongyi-MAI/Z-Image-Turbo | 977k |

**Статус:** не подключён — нужен HF токен (бесплатный). Если будет токен — напишу
третий image_gen плагин для Hermes.

## Zinaida-Router (8002) цепочка
Файл: `/opt/zinaida/meta_agent/zinaida_openai_proxy.py`
**Текущая цепочка (июль 2026):**
```
ORDER_CHAT = ["mistral", "gigachat", "github", "zhipu", "deepseek_flash"]
```
- **Mistral:** основной провайдер (mistral-large-latest, 2 ключа, ротация по лимитам)
- **GigaChat:** бесплатный текст (не -Max, не платить)
- **GitHub:** gpt-4.1-mini (бесплатный)
- **Zhipu:** GLM-4 Flash (бесплатный)
- **DeepSeek Flash:** платный — в самом конце как запасной

**Важные настройки:**
- `ORDER_CHAT`, `ORDER_CODE`, `ORDER_CREATIVE` — три независимые цепочки (все сейчас одинаковые)
- `PROVIDERS["mistral"]["model"]` должно быть `mistral-large-latest`, не `mistral-small`
- `PROVIDERS["gigachat"]["model"]` должно быть `GigaChat` (бесплатно), не `GigaChat-Max` (платно)
- `load_env()` читает `/opt/zinaida/.env` — ключи должны быть там
