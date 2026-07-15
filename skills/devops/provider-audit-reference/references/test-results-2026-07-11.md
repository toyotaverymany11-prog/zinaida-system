# Provider Test Results — 11.07.2026 (Техник 7)

## Ключевое открытие: model_catalog vs custom_providers

При попытке удалить `custom:deepseek` и `copilot` из списка провайдеров Hermes Studio выяснилось:

- **DELETE API** возвращает `{"success": true}` (HTTP 200) даже когда провайдер не удалён
- **Причина:** `custom:deepseek` и `copilot` — это **built-in model_catalog** провайдеры, а не пользовательские
- **Проверка:** `/root/.hermes/config.yaml` → `custom_providers:` — там только zinaida-router, zina2-router, 8005
- **Вывод:** built-in провайдеры read-only, их нельзя удалить через API

## Попытки удалить copilot и custom:deepseek

| Попытка | Метод | Результат |
|---------|-------|-----------|
| `hermes_studio_use_provider_delete(pool_key="copilot")` | MCP API | success: true, но провайдер остался |
| `hermes_studio_use_provider_delete(pool_key="custom:deepseek")` | MCP API | "not found" |
| `DELETE /api/hermes/config/providers/custom:deepseek` | HTTP API | 404 "not found" |
| `DELETE /api/hermes/config/providers/deepseek?source=custom_providers&providerKey=deepseek` | HTTP API | success: true, но ничего не изменилось |
| `DELETE /api/hermes/config/providers/deepseek` | HTTP API с токеном | success: true, но ничего не изменилось |
| `DELETE /api/hermes/config/providers/copilot` | HTTP API с токеном | success: true (copilot в ответе исчез, но в списке остался) |
| Удаление кеша `provider-model-catalog.json` | Файловая система | Не помогло — кеш пересоздался |

**Итог:** Все эти провайдеры — built-in model_catalog, read-only.

## Router 8005: тест скорости

**До упрощения:** 4.5 сек (включая GigaChat + Mistral предобработку)
**После упрощения (убрали GigaChat + Mistral):**
- Короткий запрос ("Привет"): **1.3 сек**
- Длинный пост (50+ слов): **4.6 сек**
- **Сравнение с 8003 (Zina2-Router v1):** 6.3 сек → **8005 быстрее на 27%**

## Что упрощено в 8005

| Этап | Было | Стало |
|------|------|-------|
| Mistral предобработка | Чистила запрос (+1-2 сек) | **Отключена** — DeepSeek сам справляется |
| GigaChat редактура | Правила русский (+3-4 сек) | **Отключена** — 3 сек rate limit |
| Mistral верификация | Проверяла галлюцинации | **Отключена** — без GigaChat бесполезна |
| Фикс рода | Замена глаголов | **Оставлен** |

## Новый systemd сервис

- Имя: `zina2-router-8005.service`
- Порт: 8005
- Файл: `/opt/zinaida/meta_agent/router_8005_v2.py`
- Статус: ✅ active (enabled, автозапуск)
