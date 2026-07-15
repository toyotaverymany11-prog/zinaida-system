# Hermes Studio Dashboard Plugin — архитектура

**Дата:** 11.07.2026
**Плагин:** deep-research-agents
**Путь:** `/opt/zinaida/hermes-plugin-deep-research/`
**Установлен:** `/root/.hermes/plugins/deep-research-agents/` (symlink)
**Статус:** enabled (требует Ctrl+Shift+R в браузере чтобы появилась вкладка)

## Структура плагина

```
plugin.yaml                    # мета: имя, версия, описание
dashboard/
├── manifest.json               # регистрация вкладки в боковой панели
├── dist/
│   ├── index.js                # React-компонент (использует window.__HERMES_PLUGIN_SDK__)
│   └── style.css               # стили и анимации
└── plugin_api.py               # бэкенд: API эндпоинты (/api/plugins/deep-research-agents/status)
```

## Hermes Dashboard Plugin API

**SDK:** `window.__HERMES_PLUGIN_SDK__`
**React:** `sdk.React`, `sdk.hooks` (useState, useEffect, useCallback, useRef, useMemo)
**Рендер:** `React.createElement` (h) — никакого JSX, всё через h()
**Регистрация:** `sdk.registerTab(path, Component)` или `sdk.Dashboard.registerTab()`
**Таб в manifest.json:**
```json
{
  "tab": {
    "path": "/deep-research",
    "position": "after:mindscape"
  },
  "entry": "dist/index.js",
  "css": "dist/style.css",
  "api": "plugin_api.py"
}
```

**API:** Python-файл с декораторами `@app.route()` регистрирует эндпоинты в том же процессе Hermes Web UI.

## Установка локального плагина

1. Создать структуру с plugin.yaml + dashboard/
2. Скопировать/symlink в `/root/.hermes/plugins/<имя>/`
3. `hermes plugins enable <имя>`
4. **Ctrl+Shift+R** в браузере (жёсткая перезагрузка без кэша)

## Референс (Mindscape)

Mindscape: `/root/.hermes/plugins/mindscape/` — 1811 строк JS, полный когнитивный граф с SVG и WebSocket.
Наш плагин проще — 4 карточки агентов + статус + примеры запросов.
