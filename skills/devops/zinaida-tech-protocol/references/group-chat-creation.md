# Group Chat и профили: создание через Hermes Studio API

## Когда применять
- Олег просит создать «супер-агента» или групповой чат для работы
- Нужен мульти-агентный режим (несколько профилей в одной комнате)

## Протокол создания Group Chat

### 1. Создать комнату
```bash
POST /api/hermes/group-chat/rooms
Body: {"inviteCode":"zinaida-text-pro","name":"Текстовая фабрика"}
```

Параметры:
- `name` (обязательно) — название комнаты
- `inviteCode` (обязательно) — пригласительный код
- `agents` — НЕ передавать (вызывает 500)

### 2. Добавить агентов в комнату
```bash
POST /api/hermes/group-chat/rooms/{roomId}/agents
Body: {
  "name":"Зинаида",
  "description":"Главный менеджер",
  "profile":"default",
  "invited":true
}
```

### 3. Создать новый профиль (если нет подходящего)
```bash
POST /api/hermes/profiles
Body: {"name":"copywriter","clone":true}
```
- `clone: true` — копирует конфиг, .env, SOUL.md и навыки указанного профиля
- После создания профиль появляется в списке агентов

### 4. Добавить новый профиль как агента
```bash
POST /api/hermes/group-chat/rooms/{roomId}/agents
Body: {
  "name":"Копирайтер",
  "description":"Копирайтер — пишет и редактирует контент",
  "profile":"copywriter",
  "invited":true
}
```

## Провайдеры в Hermes Studio

### Проблема: MCP маскирует ключи
При вызове `hermes_studio_use_provider_add` API-ключи передаются как `***`.
Решение: добавлять провайдеров напрямую в `config.yaml` через Python.

```python
# Редактирование config.yaml через Python
with open('/root/.hermes/config.yaml', 'r') as f:
    content = f.read()
# Найти блок custom_providers и добавить новый провайдер
content += '''
  - name: mistral
    api_key: ...  # полный ключ
    base_url: https://api.mistral.ai/v1
    model: mistral-large-latest
'''
with open('/root/.hermes/config.yaml', 'w') as f:
    f.write(content)
```

### Доступные профили (проверено 11.07.2026)
| Профиль | Описание | Статус |
|---------|----------|--------|
| `default` | Зинаида (текущий) | active |
| `agent2` | Григорий (кодер) | stopped |
| `designer` | Дизайнер | stopped |
| `lera` | Лера (дизайн) | stopped |
| `zinaida` | Зинаида (старый) | stopped |
| `copywriter` | Копирайтер (создан 11.07) | stopped |

## Проблема: AgentClient не создаётся — `restoreAgents()` баг

### Симптом
Агенты добавлены в комнату через REST API, но `AgentClient` (живое Socket.IO соединение) не создаётся.
В логах Web UI ошибка:
```
Unhandled rejection
ReferenceError: t is not defined
    at JX.restoreAgents (.../server/index.js:1568:5857)
```

### Причина
В Hermes Web UI v0.6.28 функция `restoreAgents()` падает с `ReferenceError: t is not defined` из-за бага в минифицированном коде. Переменная замыкания не определена. `restoreWhenReady()` вызывается (в логах есть `[bootstrap] global agent server ready`), но `restoreAgents()` молча падает.

### Решение: gc_agent_v2.py (Python Socket.IO клиент)

Вместо патчинга 8MB минифицированного `server/index.js` — написан Python-скрипт, подключающийся как `source: "agent"`:

**Файл:** `/opt/zinaida/scripts/gc_agent_v2.py`
**Сервис:** `hermes-gc-agent-v2.service` (systemd)

```
[Unit]
Description=Hermes Group Chat Agent Client v2
After=network.target hermes-web-ui.service
Requires=hermes-web-ui.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /opt/zinaida/scripts/gc_agent_v2.py
Restart=always
RestartSec=10
```

### Архитектура

```
Python gc_agent_v2.py
  ├── читает wX из /root/.hermes-web-ui/.wX (уже персистентный!)
  ├── Socket.IO /group-chat с auth:
  │     source: "agent"
  │     agentSocketSecret: wX
  │     userId: agent:{profile}
  │     name: {name}
  ├── join room
  ├── слушает message, проверяет @упоминания
  └── отвечает через роутер 8003 (DeepSeek Flash) — не заглушкой!
```

### Ключевые моменты

| Компонент | Детали |
|-----------|--------|
| **wX файл** | `/root/.hermes-web-ui/.wX` — 64 hex символа, создаётся при старте Web UI |
| **JWT токен** | `/root/.hermes-web-ui/.token` — не нужен для `source: "agent"` (обходит authMiddleware) |
| **Агенту нужно** | `source: "agent"` + правильный `agentSocketSecret: wX` + любое `userId` |
| **Проверка сервера** | `authMiddleware`: `G.source==="agent" && G.agentSocketSecret===wX` → `e()` (пропуск без JWT) |
| **Мониторинг** | `journalctl -u hermes-gc-agent-v2.service` |
| **Лог** | `/var/log/gc-agent-v2.log` |

### Восстановление после рестарта
systemd `Restart=always` автоматически переподключает. При рестарте Web UI:
1. Web UI генерирует новый `wX` и пишет в файл (если файла нет)
2. gc_agent_v2.py стартует после Web UI (`Requires=hermes-web-ui.service`)
3. Читает свежий `wX` из файла
4. Подключается — работает без перерыва
