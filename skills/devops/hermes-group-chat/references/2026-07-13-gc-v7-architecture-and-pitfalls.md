# Group Chat v7 — Архитектура, открытия и pitfalls (13.07.2026)

## Контекст
Олег потребовал настроить групповой чат с двумя AI-агентами (Ольга + Зинаида). 
После 7 итераций выяснились фундаментальные ограничения Hermes Web UI v0.6.28.

## Фундаментальные открытия

### 1. Клиентский emit не ретранслируется другим клиентам
**Симптом:** `sio.emit("message", {...})` → сообщение сохраняется в БД, но не приходит другим сокетам.
**Причина:** `handleMessage` на сервере вызывает `nsp.to(t).emit("message", W)` ТОЛЬКО после полной валидации:
- `canSocketManageRoom` — проверяет `authUser`, `role === "super_admin"`
- `hasOnlineMember` — сокет должен быть онлайн в комнате
- При подключении как `source: "human"` с произвольным userId — join может не пройти

**Обход:** Прямая запись в `gc_messages` SQLite + уведомление пользователя обновить страницу.

### 2. source: "agent" с wX не работает для внешних клиентов
**Симптом:** authMiddleware пропускает (`source === "agent" && agentSocketSecret === wX`), но `handleJoin` проверяет:
```js
let a = this.storage.getRoomAgentByAgentId(b, t);
if (n === "agent" && !a) { error("Access denied"); return }
```
Если `userId` не совпадает с `agentId` в `gc_room_agents` — Access denied.

### 3. restoreAgents() падает с ReferenceError в v0.6.28
**Ошибка:** `ReferenceError: t is not defined` в `JX.restoreAgents` (строка ~1568 минифицированного кода).
**Причина:** Баг минификации — переменная `t` не определена внутри замыкания.
**Проверка:** `grep "ReferenceError.*restoreAgents" /var/log/hermes-web-ui.log`
**Workaround:** Внешний Python Socket.IO клиент. Обновление до 0.6.29 может починить.

### 4. senderName не подменяется через emit
Любой `emit("message", {"senderName": "Ольга"})` — сервер ставит `senderName` из JWT auth.
Для отображения другого имени нужно подключаться с другим userId.

## Скрипты на 13.07.2026

### gc_agent_v7.py (текущая рабочая)
- Путь: `/opt/zinaida/scripts/gc_agent_v7.py`
- systemd: `hermes-gc-v7.service`
- Лог: `/var/log/gc-agent-v7.log`
- Отвечает на `@Ольга` и `@Зинаида` через DeepSeek 8003
- Пишет ответы в БД + эмитит через Socket.IO

### gc_test_standalone.py
- Путь: `/opt/zinaida/scripts/gc_test_standalone.py`
- Одиночный тест: подключается, отправляет `@Зинаида`, ждёт 15 сек

### gc_test_callback.py
- Путь: `/opt/zinaida/scripts/gc_test_callback.py`
- Тест с callback: join и message с callback для отлова ошибок

## Ключевые пути
| Файл | Назначение |
|------|-----------|
| `/opt/zinaida/scripts/gc_agent_v7.py` | ✅ Рабочий агент |
| `/var/log/gc-agent-v7.log` | Лог v7 |
| `/root/.hermes-web-ui/hermes-web-ui.db` | SQLite БД Web UI |
| `/root/.hermes-web-ui/.wX` | agentSocketSecret (64 hex) |
| `/root/.hermes-web-ui/.token` | HMAC secret для JWT |
| `/usr/local/lib/node_modules/hermes-web-ui/dist/server/index.js` | Сервер (8MB) |
| `/var/log/hermes-web-ui.log` | Лог Web UI |

## Команды диагностики
```bash
# Проверить сервис
systemctl is-active hermes-gc-v7.service
systemctl status hermes-gc-v7.service

# Лог агента
tail -20 /var/log/gc-agent-v7.log

# Лог Web UI — ошибки агентов
grep -i "restoreAgents\|ReferenceError\|GroupChat\|AgentClients" /var/log/hermes-web-ui.log

# Агенты в БД
sqlite3 /root/.hermes-web-ui/hermes-web-ui.db "SELECT * FROM gc_room_agents"
sqlite3 /root/.hermes-web-ui/hermes-web-ui.db "SELECT senderName, substr(content,1,60) FROM gc_messages WHERE roomId='mrj9nkx8nln7lx' ORDER BY timestamp DESC LIMIT 10"

# Сообщения от агента
sqlite3 /root/.hermes-web-ui/hermes-web-ui.db "SELECT senderName, count(*) FROM gc_messages WHERE roomId='mrj9nkx8nln7lx' GROUP BY senderName"
```
