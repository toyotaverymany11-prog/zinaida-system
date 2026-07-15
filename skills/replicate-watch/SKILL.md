---
name: replicate-watch
description: "Ежедневный мониторинг Replicate API, форумов, новых моделей. Профессиональный рост дизайнера."
version: 1.0.0
author: Zinaida-System
tags: [replicate, monitoring, research, professional-growth]
---

# Replicate Watch — Мониторинг экосистемы генерации изображений

## Для кого
Для Леры (дизайнер) и Зинаиды (контроль качества). Используется при запуске утреннего консилиума или при поиске новых техник генерации.

## Когда запускать
- Ежедневно — при старте сессии Леры
- По запросу Зинаиды: «Лера, проверь что нового по Replicate»
- Раз в неделю — глубокий дайджест

## Что мониторить — конкретные URL и запросы

### 1. Replicate (официальные ресурсы)
| Ресурс | URL | Что смотреть |
|--------|-----|-------------|
| Changelog | https://replicate.com/changelog | Новые модели, изменения API, обновления |
| Explore | https://replicate.com/explore | Новые модели по тегам image, face, skin |
| Docs | https://replicate.com/docs | API изменения, новые эндпоинты |
| FLUX | https://replicate.com/black-forest-labs | Новые версии FLUX |
| Recraft | https://replicate.com/recraft-ai | Обновления Recraft |
| Ideogram | https://replicate.com/ideogram-ai | Ideogram V3, изменения |

### 2. Форумы и сообщества (через Tavily поиск)
| Что ищем | Tavily-запрос |
|----------|--------------|
| Техники лица/кожи | `site:reddit.com/r/StableDiffusion realistic face skin generation 2026` |
| Фотореализм портреты | `site:reddit.com/r/StableDiffusionXL photorealistic portrait prompt` |
| IP-Adapter воркфлоу | `site:reddit.com/r/comfyui IP-Adapter face workflow` |
| LoRA для лиц | `site:civitai.com FLUX LoRA skin face` |
| Новые диффузионные модели | `site:huggingface.co diffusion model face generation` |
| Инструменты обучения | `site:github.com flux LoRA face training face` |

### 3. Техники генерации — ключевые слова для поиска
- `IP-Adapter FaceID update` — обновления версий
- `FLUX LoRA face training portrait` — обучение для лиц
- `realistic skin texture prompt` — промпты кожи
- `flux dev realistic portrait` — портреты
- `russian text flux lora` — русский текст на картинках
- `face consistency across angles` — консистентность лица
- `subsurface scattering skin` — реалистичная кожа

## Формат дайджеста
После изучения — пиши дайджест в `/opt/zinaida/shared_memory/lera_research/DIGEST_YYYY-MM-DD.md`:
```markdown
# Дайджест 2026-07-08

## Новые модели
- ...

## Что узнала
- ...

## Что стоит попробовать
- ...

## Техники по коже/лицам
- ...
```

## Еженедельный апдейт для Зинаиды
Раз в неделю собирай самое важное из дайджестов и добавляй в `/opt/zinaida/shared_memory/lera_research/WEEKLY_YYYY-MM-DD.md`

## Бесплатные инструменты
### GitHub Models (GPT-4o mini) — 150 запросов/день бесплатно
- Эндпоинт: `https://models.github.ai/inference/chat/completions`
- Токен: GitHub PAT с `models:read` (не классический, а со специальным скоупом)
- Используй для: анализа картинок, сравнения стилей, поиска
- Навык: `github-models-vision`
- Если 429 — лимит на сегодня исчерпан, жди следующего дня или используй второй токен

### Связь с консилиумом
Результаты ежедневного мониторинга Лера складывает в `/opt/zinaida/shared_memory/lera_research/`.
Оттуда скрипт консилиума (6:00 cron) забирает материал и формирует дайджест в `/opt/zinaida/shared_memory/consilium/replicate/`.
Полный pipe описан в навыке `consilium-collect`.

## Референсы
- `references/monitoring-urls.md` — конкретные URL для ежедневного мониторинга (Replicate, Reddit, Civitai, Hugging Face)
