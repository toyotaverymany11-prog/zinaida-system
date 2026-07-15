# Image Generation Fallback Strategy

Цель: при падении одного провайдера генерации изображений — автоматический проброс на следующий без остановки конвейера.

## Priority chain

1. **Replicate** (`replicate-image-gen` skill)
   - Модели: FLUX Dev, Recraft V3, Ideogram V3
   - Fail: 401 (token expired), 429 (rate limit), connection error
   
2. **apikey-image-gen** (Hermes Web UI → fun-codex provider)
   - Модель: gpt-5.5 / gpt-image-2
   - Доступен всегда, если Hermes Web UI жив

3. **Manual** — если оба провайдера упали, сообщить оператору и ждать инструкций

## Когда переключаться

- После **1** ошибки Replicate (401/429) → сразу пробовать apikey-image-gen
- Не ретраить Replicate 3+ раза — это тратит время и раздражает оператора
- Если apikey-image-gen тоже падает — сообщить оператору: «Оба провайдера отказали. Нужен новый Replicate-токен или починка Hermes Web UI»

## Примеры из реальных сессий

### 2026-07-08: Генерация портретов Зинаиды
- Replicate: 30/35 генераций провалились по 401 (токен протух)
- apikey-image-gen не пробовался (не было fallback)
- Итог: только 5/35 ракурсов успешно, остальное — потерянный цикл
- **Урок:** при первом 401 на Replicate → сразу fallback на apikey-image-gen
