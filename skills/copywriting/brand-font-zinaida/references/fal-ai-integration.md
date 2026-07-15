# FAL.ai — интеграция с Hermes

## Что это
Hermes Agent поддерживает FAL.ai **из коробки** через встроенный `image_generate` тул.
Не нужно писать скрипты, дёргать API из терминала, обрабатывать polling.

## Настройка
1. Зарегиться на https://fal.ai
2. Получить API ключ (Dashboard → API Keys)
3. Добавить в `.env`:
```
FAL_KEY=твой-ключ-тут
```
4. В `~/.hermes/config.yaml`:
```yaml
image_gen:
  enabled: true
  model: fal-ai/nano-banana-pro  # или другой
```
5. `/reset` в чате (перезагрузка сессии)

## Модели для кириллицы (сортировка по приоритету)

| Модель | ID на FAL | Скорость | Цена | Кириллица |
|--------|-----------|----------|------|-----------|
| **GPT Image 2** | `fal-ai/gpt-image-2` | ~20 сек | $0.04-0.06 | ✅ SOTA text rendering + CJK |
| **Nano Banana Pro** | `fal-ai/nano-banana-pro` | ~8 сек | $0.15/image (1K) | ✅ typography, text rendering |
| **FLUX 2 Klein** | `fal-ai/flux-2/klein/9b` | <1 сек | $0.006/MP | ⚠️ базовый, текст слабее |
| **Recraft V4 Pro** | `fal-ai/recraft/v4/pro/text-to-image` | ~8 сек | $0.25 | ⚠️ дизайн-стиль |
| **Krea 2** | `fal-ai/krea/v2/medium/text-to-image` | ~15-25 сек | $0.030-0.035 | ⚠️ иллюстрации |

## FAL vs Replicate

| Критерий | Replicate | FAL |
|----------|-----------|-----|
| Кириллица | Nano Banana 2 🏆 | GPT Image 2 / Nano Banana Pro |
| Wide-формат | Всегда квадрат 1024×1024 | Поддерживает разные размеры |
| Настройка | Скрипты через терминал | Встроенный тул Hermes |
| Цена FLUX | $0.025 | $0.006 (в 4 раза дешевле) |

## Когда использовать FAL
- Когда Nano Banana 2 на Replicate не даёт нужного wide-формата
- Когда нужно быстро без скриптов
- Когда FLUX за копейки ($0.006)
- Для тестовых генераций

## Когда НЕ использовать FAL
- Портреты Зинаиды (нужна LoRA toyotaverymany11-prog/zina — только на Replicate)
- Когда уже есть готовый результат (cover_V2*.jpg)
- Генерации с LoRA

## Команда в Hermes
После настройки: просто `сгенерируй картинку` — Hermes сам вызывает тул.
