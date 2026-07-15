# Hermes Studio: безопасная чистка провайдеров

**Кейс:** Техник 7 (11.07.2026) — дубликаты провайдеров в Hermes Studio.
**Урок из Техник 6:** Предыдущая чистка роутеров удалила ВСЕ провайдеры — systemd рухнул. Олег восстанавливал вручную.

## 🚨 КРИТИЧЕСКОЕ ПРАВИЛО: НЕ ТРОГАТЬ ПРОВАЙДЕРЫ БЕЗ СТРАХОВКИ

Любая операция с провайдерами Hermes Studio:
1. **Бэкап** — скопировать `/root/.hermes/config.yaml`
2. **Точечное действие** — удалять ОДИН провайдер за раз
3. **Проверка** — после каждого удаления убедиться что всё живо
4. **Не использовать массовые/пакетные операции**

## 🚨 КРИТИЧЕСКОЕ ОТКРЫТИЕ: BUILT-IN MODEL_CATALOG НЕ УДАЛЯЕТСЯ

**Симптом (Техник 7):** DELETE API возвращает `{"success": true}`, HTTP 200 — но провайдер остаётся. Это не баг, а фича — built-in model_catalog провайдеры read-only.

**Архитектура провайдеров Hermes Studio:**

| Тип | Откуда берётся | Где хранится | Можно удалить? |
|-----|----------------|--------------|----------------|
| **built-in (model_catalog)** | Встроенный каталог моделей | model_catalog в Web UI (JSON кеш) | **НЕТ** |
| **custom_providers** | Settings → Providers или MCP API | `/root/.hermes/config.yaml` → `custom_providers:` | **ДА** |
| **providers** (legacy) | config.yaml `providers:` секция | `/root/.hermes/config.yaml` | **ДА** |

**Как отличить:** смотреть `/root/.hermes/config.yaml` → `custom_providers:`.
Если провайдера там нет → это built-in, удалить нельзя.

**Built-in провайдеры, которые НЕЛЬЗЯ удалить (но они висят мёртвыми):**
- `deepseek` (родной DeepSeek model_catalog — v4-flash, v4-pro)
- `custom:deepseek` (старая версия DeepSeek из model_catalog — chat, reasoner, v4-0324)
- `copilot` (GitHub Copilot — 19 моделей GPT-5, требует `COPILOT_GITHUB_TOKEN`)

**Удалять можно только:** zinaida-router, zina2-router, 8005 (те что в config.yaml).

## Два API для удаления провайдеров

### MCP API (через Hermes Studio MCP)
```python
mcp_hermes_studio_use_hermes_studio_use_provider_delete(
    pool_key="custom:deepseek",
    profile="default"
)
```
Работает ТОЛЬКО для custom_providers (что в config.yaml).
Для built-in model_catalog возвращает `{"success": true}` но ничего не делает.

### Прямой HTTP API (через Bearer token)
```bash
TOKEN=$(cat /root/.hermes-web-ui/profiles/default/.model-run-token)

# Удаление custom провайдера
curl -X DELETE "http://127.0.0.1:8648/api/hermes/config/providers/deepseek?source=custom_providers&providerKey=deepseek" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Удаление built-in провайдера
curl -X DELETE "http://127.0.0.1:8648/api/hermes/config/providers/deepseek" \
  -H "Authorization: Bearer $TOKEN"
```
Оба возвращают `{"success": true}` HTTP 200 даже для model_catalog — не верить.
Единственный способ проверить: `mcp_hermes_studio_use_hermes_studio_use_available_models()` после DELETE.

## 3-точечная верификация роутера/провайдера

| Точка | Инструмент | Что даёт |
|-------|-----------|----------|
| Hermes Studio | `available_models(query="...")` | Есть ли в конфиге |
| Порт | `ss -tlnp \| grep ПОРТ` | Реально ли слушает, PID |
| HTTP | `curl http://127.0.0.1:ПОРТ/v1/models` | Отвечает ли, код, скорость |
| Systemd | `systemctl status имя.service` | Сервис ли это |

Если нет порта — роутер мёртв, даже если прописан в Hermes.

## Выявление дубликатов

**Кейс:** deepseek (built-in, v4-flash, v4-pro) vs custom:deepseek (chat, reasoner, v4-0324).
Это РАЗНЫЕ версии DeepSeek — не дубликаты. Просто model_catalog показывает обе.

**Правило:** если провайдер есть в config.yaml → пользовательский. Если нет → model_catalog.

## Паттерн: мёртвый кастомный роутер (кейс 8005)

- Файл есть: `/opt/zinaida/meta_agent/router_8005_v2.py`
- В Hermes прописан: `custom:8005` → `http://127.0.0.1:8005/v1`
- Реальность: порт пуст, systemd-сервиса нет
- Почему мёртв: файл написан, сервис не создан
- После Техник 7: создан systemd сервис `zina2-router-8005.service`, все 5 усилителей работают (Mistral, Ollama, GigaChat, RAG, Fallback)

## Copilot: статус

Провайдер `copilot` (GitHub Copilot) — 19 моделей GPT-5.
Статус на 11.07.2026: ❌ нет ключа `COPILOT_GITHUB_TOKEN` + IP в ЧС РФ (403).
Удалить нельзя — built-in model_catalog. DELETE возвращает `success: true` но провайдер остаётся.
