# Провайдеры из model_catalog — не удаляются

Некоторые провайдеры в Hermes Studio выглядят как «лишние дубликаты», но **не являются пользовательскими**. Они встроены в model_catalog Hermes Web UI и **не удаляются** через API.

## Список таких провайдеров

| Провайдер | Почему не удалить | Модели |
|-----------|-------------------|--------|
| `deepseek` (built-in) | Встроенный провайдер DeepSeek | deepseek-v4-flash, deepseek-v4-pro |
| `custom:deepseek` | Из model_catalog, не custom_providers | deepseek-chat, deepseek-reasoner, deepseek-v4-0324, deepseek-v4-0324-fast, deepseek-v4-pro |
| `copilot` | Из model_catalog (GitHub Copilot) | gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5-mini (19 моделей) |

## Симптомы «не удаляется»

- `DELETE /api/hermes/config/providers/custom:deepseek` → HTTP 200 `{"success":true}`
- Но провайдер **остаётся** в available-models

Это потому что provider живёт в model_catalog (кеш Hermes Web UI), а не в custom_providers или providers секции config.yaml.

## Copilot (GitHub Copilot)

- Требует `COPILOT_GITHUB_TOKEN` environment variable
- В РФ может быть 403 (IP блокировка) + нет токена
- **Не удаляем** — это встроенный провайдер Hermes
- Для работы: `export COPILOT_GITHUB_TOKEN=<token>` в окружение systemd

## custom:deepseek vs deepseek (built-in)

Разница минимальная:

| Модель | `deepseek` (built-in) | `custom:deepseek` |
|---|---|---|
| deepseek-v4-flash | ✅ | ✅ |
| deepseek-v4-pro | ✅ | ✅ |
| deepseek-chat | ✅ | ✅ |
| deepseek-reasoner | ✅ | ✅ |
| deepseek-v4-0324 | ❌ | ✅ |
| deepseek-v4-0324-fast | ❌ | ✅ |

`custom:deepseek` знает больше старых версий. Все важные модели есть у обоих.
