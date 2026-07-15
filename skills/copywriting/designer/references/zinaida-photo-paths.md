# Zinaida Photo Paths — Правильные и неправильные (12.07.2026)

> Ошибка 12.07: сказала «показала фотографии Зинаиды» но скинула AI-генерации из неправильной папки. Олег: «это хуйня полнейшая, это не Зинаида».

## ✅ ПРАВИЛЬНЫЕ ФОТО (подтверждено Олегом)

### 23 сгенерированных фото (паспортные ракурсы)
```
/opt/zinaida/SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/
```
Файлы: zinaida_01.jpg ... zinaida_09_minimal.jpg, zinaida_fullbody_*.jpg, zinaida_halfbody_*.jpg, test_skin.jpg

### 3 оригинала (референсы, настоящие фото)
```
/opt/zinaida/design/references/zinaida_face/
```
- IMG_9391.JPG (262KB) — анфас, чёрная водолазка, студийный портрет
- IMG_0413.PNG (1.5MB) — 3/4 поворот, серый спортивный топ
- IMG_0415.PNG (2.0MB) — дополнительный ракурс

## ❌ НЕПРАВИЛЬНЫЕ ФОТО (AI-мусор, не Зинаида)

```
/opt/zinaida/design/passport/generated/
```
Там: front_serious.jpg, profile_left.jpg, three_quarter.jpg, dramatic_lighting.png и т.д.
Эти файлы — AI-генерации от другого провайдера, лицо на них — НЕ Зинаида.

## ПРАВИЛО

**Перед любой отправкой фото Зинаиды Олегу:**
1. Проверить что файл из ПРАВИЛЬНОЙ папки
2. Сверить с 3 оригиналами через vision_analyze
3. Только если лицо совпадает — отправлять

**LoRA для FAL обучалась на правильных 23 фото из SmmFabrika/queue/kontent/dizayner/zinaida_passport/generated/**
