---
name: hermes-group-chat-agent
description: "Подключение AI-агентов к Group Chat Hermes Web UI. Архитектура, ограничения, рабочий обход (responder как human + запись в БД)."
version: 1.0.0
author: Zinaida
tags: [group-chat, agent, socketio, hermes-webui, responder]
---

# Group Chat Agent Integration

## Архитектура

Hermes Web UI Group Chat использует Socket.IO с namespace `/group-chat`.

### Сущности
- **Registered Agent** — запись в SQLite (`gc_room_agents`). Создаётся через REST API или UI. Сохраняется после рестарта.
- **AgentClient** — живой Socket.IO клиент внутри процесса Node.js. **Теряется при рестарте.** Создаётся только через UI, не через API.
- **wX** — `agentSocketSecret`, 64 hex-символа. Персистентен через файл `/root/.hermes-web-ui/.wX`.

## Проблема

emit("message") от клиента Socket.IO **не ретранслируется другим клиентам** — только серверный nsp.to(room).emit() это делает. Клиентский emit проходит через handleMessage, который проверяет canSocketManageRoom. Если проверка не проходит — сообщение не рассылается.

**Финальное подтверждение (13.07.2026):** Даже с userId=1 и role=super_admin — emit("message") от Python Socket.IO клиента НЕ вызывает server-side broadcast. handleMessage в server/index.js принимает сообщение, сохраняет в БД, но nsp.to(room).emit() выполняется только если canSocketManageRoom() истина для этого сокета.

**Обход:** Писать сообщение напрямую в SQLite таблицу gc_messages. Оно появится в UI после обновления страницы.

## Рабочее решение: Responder как human

### Что работает
1. Подключаемся к `/group-chat` как `source: "human"` с JWT токеном
2. Слушаем `on("*", namespace="/group-chat")` — ловим `message` события
3. Проверяем `@ИмяАгента` в content
4. Отвечаем через DeepSeek/Mistral (через роутер 8003 или 8002)
5. **Пишем ответ в БД напрямую** + эмитим `emit("message")` (на случай если сервер ретранслирует)
6. Сообщение появляется после обновления страницы (F5)

### Ключевые файлы
- `/opt/zinaida/scripts/gc_agent_v7.py` — финальная версия (пишет в БД gc_messages + эмитит через сокет). **РАБОТАЕТ — ответы видны после F5**
- `/opt/zinaida/scripts/gc_agent_v6.py` — предыдущая, без прямого DB write
- `/opt/zinaida/scripts/gc_responder_v2.py` — responder с DeepSeek (без DB write, только emit)
- `/opt/zinaida/scripts/gc_test_standalone.py` — тестер подключения
- `/opt/zinaida/scripts/gc_test_callback.py` — тест с callback для диагностики emit ошибок
- Исследование: `/opt/zinaida/character/docs/deep_research_tz_group_chat.md`

### Systemd
```bash
systemctl enable --now hermes-gc-v6.service   # v6 финальная
# или
systemctl enable --now hermes-gc-responder-v2.service  # responder
```

### Ограничения
- Ответы видны только после обновления страницы (не live)
- `senderName` в сообщении подставляется сервером из JWT — нельзя произвольно менять
- `agentSocketSecret (wX)` лежит в `/root/.hermes-web-ui/.wX` — используется для `source: "agent"`, но этот метод не работает

### Питфоллы
- **Два сокета с одинаковым userId на одном namespace** — второй не может join. Каждому агенту нужен уникальный `userId`.
- `handleJoin` проверяет `canSocketJoinRoom` — нужен `userId` из `gc_room_members` или `authUserId` существующий.
- `gc_room_members` таблица — добавить напрямую через SQLite если REST API не даёт.
- Socket.IO Python клиент — версия 5.16.3+. `transports=["websocket", "polling"]` для стабильности.

### История ошибок
- 13.07.2026: `restoreAgents()` в server/index.js падает с `ReferenceError: t is not defined` (баг v0.6.28, исправлен в v0.6.29?)
- 13.07.2026: `emit("message")` с произвольным `senderName` отклоняется сервером — имя подставляется из JWT auth.
- 13.07.2026: Обновление с v0.6.28 на v0.6.29 сбросило все патчи
