# Design System Playbook — Контент-завод «Зинаида»

> Сводка по визуальному дизайну для проекта Otnoshenya.
> Собрана из: ZINAIDA_PASSPORT.md, design/config.yaml, SOUL.md Леры, стилей обложек/цитат/сцен, VK_assets.md, visual_prompts.
> Обновлено: 2026-07-09

## 1. Команда

Дизайн делает **Лера** (профиль lera, gateway порт 8645). Правило: минимум 3 варианта на задачу.

Провайдеры: 1) Replicate API (FLUX Dev, Recraft V3, Ideogram V3, IP-Adapter FaceID), 2) GigaChat, 3) FusionBrain, 4) градиент.

## 2. Типы контента (content mix)

- **Журнальные обложки (60%)** — тёмный фон, Didone-шрифт, Ideogram V3 / Recraft
- **Цитаты (25%)** — минимализм, тёплый фон, кавычки, Cormorant Garamond Italic
- **Сцены (15%)** — фотореализм, драматичный свет, bokeh, FLUX Dev + LoRA

Шаблоны промптов: /opt/zinaida/SmmFabrika/assets/visual_prompts/ (4 шт: carousel.json, quote.json, reels.json, article.json)

## 3. Размеры

VK/IG/Odnoklassniki/MessengerMax/YandexMessenger: 1080×1080. Reels/Stories: 1080×1920. Dzen: 1200×630. TG: 1280×720. Pinterest: 1000×1500.

VK-упаковка (7 изобр.): аватар 200×200, обложка десктоп 1590×400, мобильная 1080×1920, 4 плитки меню 510×510.

## 4. Бренд

Цвета: графит #121214, терракота #C05746, тёплый белый #F0EEEB, бордовый #8B0000, золото #C9A84C, глубокий синий #1B2A4A.

Шрифты: Playfair Display / Didone (заголовки), Inter/Montserrat (основной), Cormorant Garamond Italic (цитаты), Roboto (текст на картинках).

## 5. Внешность Зинаиды

Русые/светлые волосы, голубые глаза, 28 лет, стройная. Аватар: zinaida_06_serious.jpg. Референсы: /opt/zinaida/SmmFabrika/assets/photos/ (8 фото, 3 основных: IMG_0413, IMG_0415, IMG_9391).

Промпт кожи обязателен: Ultra-realistic skin texture with visible pores, natural imperfections, subsurface scattering, NOT plastic or airbrushed. Фидбек Олега: не крупный план, half/full body.

Допустимые эмоции: уверенность (40%), улыбка (30%), задумчивость (15%), ирония (10%), серьёзность (5%). Запрещено: страх, паника, слёзы, растерянность. Запрещено ставить в драматические сцены с мужчиной.

## 6. Статус

VK работает (группа aipsiholog, 5 подписчиков + личная zinadchdp), Telegram-бот (@DCHP_Shtab_bot) работает. Остальные 6 сетей не созданы. Тексты постов в очереди есть (~80 за 2-12 июля), картинок — 0.
