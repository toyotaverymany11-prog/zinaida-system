# Провайдеры и модели в Hermes Studio

## Правило: один провайдер на один порт

**НИКОГДА** не создавать несколько custom_providers на один и тот же base_url.

### ❌ НЕПРАВИЛЬНО (как было сделано 13.07.2026)
```yaml
custom_providers:
  - name: router-8005-enhanced  # ← отдельный провайдер на модель
    base_url: http://127.0.0.1:8005/v1
    model: 8005-Enhanced
  - name: router-8005             # ← ещё один на тот же порт
    base_url: http://127.0.0.1:8005/v1
    model: 8005-Router
  - name: router-8005-flash       # ← и ещё
    base_url: http://127.0.0.1:8005/v1
    model: 8005-Flash
```
Результат: в Hermes Studio отображаются 4 отдельных провайдера вместо одного с 4 моделями.

### ✅ ПРАВИЛЬНО
```yaml
custom_providers:
  - name: 8005
    base_url: http://127.0.0.1:8005/v1
    model: 8005-Enhanced  # только модель по умолчанию
```

Модели автоматически подтягиваются из API роутера (GET /v1/models). Hermes Studio группирует их под одним провайдером.

## MCP API vs прямой patch конфига

### Через MCP API (предпочтительно для добавления)
```python
mcp_hermes_studio_use_hermes_studio_use_provider_add(
    profile="zinaida",
    name="8005",
    base_url="http://127.0.0.1:8005/v1",
    api_key="local-router-key",
    model="8005-Enhanced"
)
```

**Ограничение MCP API:** не поддерживает параметр `models: [...]`. Если нужно добавить список моделей (как в корневом конфиге `models: ['8005-Enhanced', '8005-Flash']`) — добавлять через MCP API, потом вручную допатчить конфиг:

```yaml
# После MCP API — допатчить в config.yaml профиля:
  - name: "8005"
    base_url: http://127.0.0.1:8005/v1
    api_key: local-router-key
    model: 8005-Enhanced
    models:                     # ← добавить вручную
      - 8005-Enhanced
      - 8005-Flash
```

### model.default: критическая ошибка
**НИКОГДА** не ставить `model.default: Zinaida-Router` в профиле. 8002 роутер не стримит под этим именем — возвращает пустой стрим, агент зависает.
**Всегда** `model.default: deepseek-chat` (если профиль использует 8002 роутер).

После любых изменений — рестарт Gateway: `systemctl restart hermes-gateway`.
Убедиться что default профиль (я) жив после рестарта.

## Где хранить custom_providers

- **Профильные провайдеры** → `/root/.hermes/profiles/PROFILE_NAME/config.yaml`
- **Корневой конфиг (`/root/.hermes/config.yaml`)** — НЕ добавлять `custom_providers`. Только секция `providers:` (старый формат, если нужен).
- После изменения — переключиться на профиль заново (gateway перечитает конфиг).

## Принцип «Правда из кода, не из головы»

Никогда не гадать, что делает роутер. Читать код:

```bash
# Какие модели отдаёт роутер
curl -s http://127.0.0.1:8005/v1/models

# Что внутри роутера
grep -n "model\|classify\|MOA\|Enhanced" /opt/zinaida/meta_agent/router_8005_v2.py

# Классификация запросов (как выбирается flash vs pro)
grep -A 30 "def _classify_request" /opt/zinaida/meta_agent/router_8005_v2.py

# Что делает 8005-Enhanced (MOA, Pro форсирован)
grep -n "enhanced\|MOA\|_call_moa" /opt/zinaida/meta_agent/router_8005_v2.py
```

## Связь с контекстной архитектурой

Профили Hermes изолированы:
- **default** → контент-завод (использует корневой config.yaml)
- **zinaida** → разработка персонажа (имеет свой config.yaml с custom_providers)
- **agent2** → кодер (имеет свой config.yaml)

Каждый профиль может иметь свой набор провайдеров, не пересекаясь с другими.
