# Hermes Studio vs Agent Dashboard — Plugin Architecture Lesson (11.07.2026)

## Открытие
Hermes Studio (Web UI v0.6.28) и Hermes Agent Dashboard (порт 9119) — **разные системы** с разными plugin API.

## Hermes Agent Dashboard (порт 9119)
- Запуск: `hermes dashboard` (FastAPI + Uvicorn + React)
- Страницы: CHAT, SESSIONS, FILES, MODELS, LOGS, CRON, SKILLS, PLUGINS, MCP, CONFIG, KEYS
- Плагины устанавливаются через `hermes plugins install <repo> --enable`
- Dashboard-плагины (Mindscape, наш deep-research-agents) появляются как вкладки в боковой панели
- Плагин использует `window.__HERMES_PLUGIN_SDK__` + manifest.json (tab.path, position, entry)
- Чат через xterm.js (эмулятор терминала), не нативный чат
- Нет голоса
- Это админ-панель для управления агентом, не для общения

## Hermes Studio (Web UI v0.6.28, порт 8648)
- Запускается через npm как самостоятельное приложение
- Это то, в чём Олег работает каждый день
- **НЕ поддерживает кастомные Dashboard Plugin вкладки** в своей боковой панели
- Mindscape там НЕ РАБОТАЕТ — он работает только в Agent Dashboard (9119)
- Имеет свой плагин-менеджмент через API (но он для другого — auth providers, backends)
- Умеет: чат, терминал, cron, kanban, файлы, настройки
- Есть Voice Dialogue (микрофон в чате)

## Вывод
Писать Hermes Studio Dashboard Plugin — **бесполезно**, т.к. Studio не имеет API для кастомных вкладок.
Для визуализации Deep Research использовать:
1. Текст в чате с рамками и эмодзи (всегда работает)
2. HTML-страницы через Caddy (открываются по HTTPS)
3. В крайнем случае — Agent Dashboard (9119) с плагином

## Caddy HTTPS route для визуализации
```
handle_path /research/* {
    root * /opt/zinaida
    file_server
}
```
- splash: https://zinadchdp.duckdns.org/research/deep_research_splash.html
- отчёты: https://zinadchdp.duckdns.org/research/sandbox/deep_research/{folder}/report.html
- Файлы должны иметь права 644 (Caddy не может читать 600)
