# Graphify — граф знаний проекта

## Дата установки: 18.07.2026
## Версия: 0.9.19
## Репозиторий: https://github.com/Graphify-Labs/graphify (90.8k stars)

## Установка
- `pipx install graphifyy` — CLI
- `graphify install` — регистрация навыка для Hermes
- `PATH` добавлен: `~/.local/bin`

## Граф
- Папка: `/opt/zinaida/graphify-out/`
- Файлы: `graph.json` (3.2MB), `graph.html` (2.7MB), `GRAPH_REPORT.md`, `manifest.json`
- Нод: 3120, Рёбер: 5163, Сообществ: 348
- Режим: code-only (локальный, 0 токенов)
- Документы: не загружены (DeepSeek не успел за таймаут 180с)

## Использование
- `graphify query "вопрос"` — поиск по графу
- `graphify path "X" "Y"` — путь между нодами
- `graphify explain "нода"` — пояснение ноды
- `graphify update .` — обновление после изменений кода

## Тест
18.07 — установлен, построен граф кода (3120 нод).
20.07 — проверка работы (Олег, напомню в Telegram).

## Токен для семантики
DeepSeek ключ есть. Для полного графа с документами нужна команда:
`cd /opt/zinaida && graphify .` (занимает 2-4 минуты)
