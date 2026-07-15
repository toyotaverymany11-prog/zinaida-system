---
name: hermes-display-tool-progress
description: Как убрать технический мусор (результаты terminal, read_file, patch) из чата Hermes Studio через display.tool_progress.
version: 1.0
author: Zinaida
triggers:
  - tool_progress
  - мусор в чате
  - технический мусор
  - лишние логи в чате
  - скрыть tool call
  - hide tool output
  - clean chat
  - убрать terminal из чата
  - не показывать результаты команд
---

# Hermes Studio — как убрать технический мусор из чата

## Проблема
В чате Hermes Studio отображаются результаты вызовов инструментов (terminal, read_file, patch и т.д.) перед ответами. Это засоряет чат технической информацией.

## Решение
Установить `display.tool_progress: off` в config.yaml через штатную команду:

```bash
hermes config set display.tool_progress off
```

## Варианты
| Значение | Эффект |
|----------|--------|
| `off` | Не показывать tool calls вообще |
| `new` | Показывать только новые |
| `all` | Показывать все (по умолчанию) |
| `verbose` | Подробный режим |

## Где применяется
Глобально для всех платформ (CLI, Web UI, Telegram, Slack, Discord и т.д.).

## Источники
- Reddit: r/hermesagent — пост `[ask]hide tools call`
- GitHub issue #34653: `hermes config show` omits display.* keys
- Mintlify документация: `display.tool_progress: "all" # off | new | all | verbose`
- GitHub issue #6164: Feature: per-platform tool_progress overrides

## Важно
- Применять ТОЛЬКО через `hermes config set`, не через sed/python напрямую.
- После установки перезагрузить страницу Hermes Studio (F5 или Ctrl+Shift+R).
- Для Telegram есть отдельная настройка: `display.platform.telegram.tool_progress: off`

## Дополнительные настройки отображения
```yaml
display:
  compact: false          # компактный режим
  show_reasoning: false   # скрыть reasoning блоки
  tool_progress: off      # скрыть tool output
  tool_progress_command: false # скрыть команды
```
