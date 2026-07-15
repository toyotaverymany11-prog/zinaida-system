# Group Chat — 13.07.2026 сессия: v6/v7 и отключение DeepSeek

## Контекст
Олег: DeepSeek закончились деньги, нашёл это через platform.deepseek.com/usage.
Обвинил что роутеры не работают без DeepSeek — хотя бесплатные модели должны отвечать.
Параллельно тестировали групповой чат.

## Проблема: emit("message") не ретранслируется

**Симптом:** `sio.emit("message", {"roomId": ROOM, "content": reply})` — сообщение ПИШЕТСЯ в `gc_messages` (БД), 
но НЕ приходит другим клиентам в реальном времени. Видно только после F5.

**Корень:** клиентский `emit("message")` → сервер вызывает `handleMessage` → тот проверяет 
`canSocketManageRoom` и `hasOnlineMember`. Если сокет не прошёл — `nsp.to(room).emit("message", W)` НЕ вызывается.

**Обход:** писать напрямую в SQLite:
```python
conn.execute("INSERT INTO gc_messages (id, roomId, senderId, senderName, content, timestamp, role) VALUES (?,?,?,?,?,?,?)",
    (mid, ROOM, sid, name, content, ts, "user"))
```

**Живой ответ** — только через исправление server/index.js (8MB минифицированного кода) или обновление до версии где это починят.

## Эволюция скриптов (что пробовали)

1. **responder** (старый, `gc_responder.py`) — заглушка, отвечал "слушаю!". РАБОТАЛ в исследовании.
2. **agent_v2** — source:agent с wX. `Not in room` — не работал.
3. **olya+zinaida** — два отдельных процесса. source:agent. Not in room.
4. **agent_v4** — один сокет super_admin, отвечает на @. emit не доходит до других.
5. **agent_v5** — два сокета + worker thread. Сложно, ненадёжно.
6. **agent_v6** — один сокет + запись в БД. ✅ Ответ есть, виден после F5.
7. **responder_v2** — как старый responder, но с DeepSeek. Выяснили: emit не работает.
8. **v6.29** — обновление Web UI до v0.6.29. restoreAgents() не починили.

**Текущая:** v7 (`gc_agent_v7.py`) — пишет в БД + эмитит в Socket.IO.
systemd: `hermes-gc-v7.service` (не active — отключён после тестов).

## 8002 — страховочный роутер без DeepSeek

**Проблема:** 8002 (zinaida_openai_proxy.py) имел DeepSeek в ORDER_CHAT.
Когда DeepSeek пустой (402) — fallback шёл на DeepSeek, падал, потом на Mistral.

**Фикс (13.07.2026):**
- Убрала DeepSeek из ORDER_CHAT, ORDER_CODE, ORDER_CREATIVE
- Вместо `deepseek_flash` — `gigachat` и `zhipu` (тоже бесплатные)
- Удалила `FREE_PROVIDERS` (он ссылался на deepseek_flash)
- Переделала race pool: берёт топ-2 из alive_order (все бесплатные)
- **Результат:** 8002 полностью независим от DeepSeek. Тестировала: Mistral ответил на короткий, GitHub gpt-4.1-mini на сложный.

**Важно:** 8005 (router_8005_v2.py) — **НЕ ТРОГАТЬ**. Олег запретил. 
DeepSeek в 8005 падает на Pro-запросах (строка 690: `if model_key != "pro"` — Pro идёт сразу на DeepSeek, минуя cascade). 
Если DeepSeek мёртв и надо чинить 8005 — только с разрешения Олега.

## Правило "сначала почини потом скажи" (вывод)

Олег EXPLICITLY сказал: «сначала почини все удостоверься а потом меня дёргай».
Это значит: ни слова Олегу пока фикс не завершён, протестирован и не работающий.
Никаких "щас отправлю", "сейчас проверю", "давай протестируем" — сначала сделать, потом сказать.
