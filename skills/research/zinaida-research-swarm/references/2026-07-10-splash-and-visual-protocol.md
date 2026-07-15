# HTML Splash Page and Visual Protocol (10.07.2026)

## Splash Page (`/opt/zinaida/deep_research_splash.html`)

Создана HTML-заставка для Deep Research, открывается в браузере при старте.

### Дизайн
- Тёмная тема (#0a0a0f), белый текст
- 4 карточки агентов в grid (Mistral, GitHub, Ollama, DeepSeek)
- Каждая: аватар с буквой, имя, роль, описание, бейдж (Бесплатно/Pro)
- Анимация fadeIn и slideUp для последовательного появления карточек
- Блок Зинаиды с фиолетовым градиентом, личное обращение
- 3 примера запросов, поле ввода с кнопкой

### Файлы
- `/opt/zinaida/deep_research_splash.html` — основной HTML
- CSS inline, Google Fonts (Inter), CSS keyframes
- Самодостаточный, без сервера

## Проблема: визуал в чате vs в браузере

Hermes Studio — текстовый чат. Анимация/карточки/интерактив невозможны.
- **Можно:** открыть splash.html в браузере (file:///path), показать скриншот как MEDIA
- **Нельзя:** анимированный визуал в окне Hermes Studio

## report.html

Автоматически генерируется в конце исследования: карточки агентов, дебаты, добивка, вердикт DeepSeek.

## Mindscape plugin

Для обычных чатов: `hermes plugins install southy404/hermes-mindscape --enable`
Показывает когнитивный граф одного агента. Нужен рестарт gateway.
