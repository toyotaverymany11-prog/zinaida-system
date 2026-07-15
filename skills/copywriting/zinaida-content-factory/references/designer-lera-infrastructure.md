# Designer Лера — Infrastructure Reference

Created: 2026-07-08
Profile renamed from: grigoriy → lera

## Profile Location
- Config: `/root/.hermes/profiles/lera/config.yaml`
- SOUL.md: `/root/.hermes/profiles/lera/SOUL.md` (личность, 24 года, Краснодар)
- .hermes.md: `/root/.hermes/profiles/lera/.hermes.md` (операционные инструкции)
- MEMORY.md: `/root/.hermes/profiles/lera/MEMORY.md` (81 строка, память)
- Gateway: systemd-сервис `hermes-gateway-lera.service`, порт 8645, активен
- Модель: Zinaida-Router через custom provider (порт 8002)

## Skills (12 шт)
1. `generate-magazine-cover` — журнальные обложки (60% задач)
2. `generate-quote` — цитаты-провокации (25%)
3. `generate-scene` — эмоциональные сцены (15%)
4. `study-replicate` — еженедельный мониторинг Replicate
5. `compare-face-models` — тестирование моделей, критерии оценки
6. `software-development` — общий скил
7. `apikey-image-gen` — генерация через Hermes Web UI
8. `tavily-search` — веб-поиск через Tavily
9. `replicate-watch` — ежедневный мониторинг экосистемы генерации
10. `github-models-vision` — бесплатный vision через GitHub
11. `replicate-face-passport` — паспорт лица (из старого designer)
12. `consilium-collect` — сбор новостей для консилиума

## Replicate API
- Токен: REPLICATE_API_TOKEN в `/opt/zinaida/config/secrets.env`
- Модели: Recraft V3 (обложки), FLUX Dev (фотореализм), Ideogram V3 (текст), IP-Adapter FaceID (лицо)
- Приоритет: Replicate → GigaChat → FusionBrain → градиент
- Бюджет: ~$10 на счёте
- Тест-скрипт: `/opt/zinaida/design/test_replicate.py`

## Стили и библиотеки
- Стили обложек: `/opt/zinaida/design/styles/magazine_covers/` (+ README)
- Стили цитат: `/opt/zinaida/design/styles/quotes/` (+ README)
- Стили сцен: `/opt/zinaida/design/styles/scenes/` (+ README)
- Референсы: `/opt/zinaida/design/references/` (3 подпапки: competitors, font_refs, zinaida_face)
- Промпты: `/opt/zinaida/prompts/replicate_library.json` (2.7KB)
- Реалистичная кожа: `Ultra-realistic skin texture with visible pores, natural imperfections, subsurface scattering, NOT plastic or airbrushed`

## Бренд-айдентика
- Цвета: графит #121214, терракота #C05746, тёплый белый #F0EEEB
- Шрифты: Didone (Playfair Display, Bodoni Moda, Cormorant Garamond)
- Размеры: VK/IG 1080x1080, Reels 1080x1920, Dzen 1200x630, TG 1280x720

## База знаний (самообучение)
- `/opt/zinaida/shared_memory/lera_research/` — ежедневные дайджесты DIGEST_YYYY-MM-DD.md
- `/opt/zinaida/shared_memory/lera_research/TODAY.md` — план на день
- `/opt/zinaida/shared_memory/lera_research/WEEKLY_YYYY-MM-DD.md` — еженедельные сводки

## Правило работы
- Минимум 3 варианта на задачу
- Ответ начинается с «[ЛЕРА]»
- Одобренные дизайны → `/opt/zinaida/shared_memory/approved_designs/` + заметка
- Правки visual_adapter.py → делегировать agent2
