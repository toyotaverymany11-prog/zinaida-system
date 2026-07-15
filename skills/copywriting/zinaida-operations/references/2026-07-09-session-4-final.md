# Сессия 09.07.2026, часть 4 — Голосовой UI, WebSocket-агент, финальная сборка

## Ключевые уроки и исправления

### 1. Язык ответов: ТОЛЬКО русский, НИКАКОГО английского

**ПОВТОРНАЯ КРИТИКА Олега (09.07.2026):** Написал «заебала уже блядь» про английские слова в чате.

Правило уже было в AGENTS.md и SKILL.md, но НЕ соблюдалось. Ужесточаю:
- Ни одного английского слова в ответах оператору. Ни «OK», ни «done», ни «check», ни «error».
- Даже в технических описаниях — русский. «Сервер работает», а не «server OK».
- AI-термины: «роутер», «прокси», «аватар», «запрос» — русские аналоги.
- Исключения только: JSON, HTTP, URL, DNS, API (устоявшиеся аббревиатуры без русского аналога).

**Причина:** Олег теряет деньги на токенах, которые тратятся на английский текст. Каждое английское слово = пустая трата.

### 2. Проверка ссылок — снова провал (studio.sber.ru)

Не проверила studio.sber.ru перед отправкой. ERR_NAME_NOT_RESOLVED. Олег в ярости.

Правило (дубль, жёстко): прежде чем отправить Олегу любую ссылку:
1. browser_navigate(url) — проверить что открывается
2. Только если success=true — отправлять
3. Если не открывается — найти альтернативу

### 3. Caddy конфиг для zinaida (HTTPS + прокси)

Добавлены пути в Caddyfile на zinadchdp.duckdns.org:

```
handle_path /zinaida/* {
    root * /opt/zinaida/livekit/zinaida-ui
    file_server
}
handle_path /zinaida-token/* {
    reverse_proxy localhost:7890
}
handle_path /zinaida-ws* {
    reverse_proxy localhost:7892
}
```

### 4. WebSocket Voice Agent (Zinaida WS сервер)

Вместо сложного LiveKit Agent SDK — простой WebSocket сервер на aiohttp.

**Скрипт:** `/opt/zinaida/livekit/zinaida_wss.py`
**Порт:** 7892 (прокси через Caddy: /zinaida-ws → localhost:7892)

**Пайплайн (браузер → сервер):**
1. Браузер открывает WebSocket wss://zinadchdp.duckdns.org/zinaida-ws
2. Отправляет JSON: {"type": "text", "text": "..."}
3. Сервер вызывает call_router(text) → получает ответ
4. Генерирует аудио через Silero TTS (v5, kseniya, 48kHz)
5. Отправляет ответ: {"type": "response", "text": "...", "audio": "<base64 wav>"}
6. Браузер проигрывает через Web Audio API

**Не требует:** LiveKit SDK, Deepgram SDK, сложной настройки WebRTC.
**Работает:** через любой браузер с WebSocket (Safari, Chrome, iPad).

### 5. Silero TTS v5 — подтверждённый голос

**Модель:** v5_ru (139MB, скачивается при первом запуске)
**Голос:** kseniya (выбран и подтверждён Олегом 09.07.2026)
**Качество:** 48kHz, заметно лучше v4
**Скорость:** ~0.3 сек на 100 символов на CPU

### 6. Статус всех сервисов (на конец сессии 09.07.2026)

| Сервис | Порт | Статус |
|--------|------|--------|
| LiveKit (WebRTC) | 7880 | ✅ Docker, 0.0.0.0 |
| Redis | 6379 | ✅ Docker |
| Токен-сервер | 7890 | ✅ python3 bg |
| UI (HTTP) | 7891 | ⛔ остановлен (через Caddy) |
| WS агент | 7892 | ✅ python3 bg |
| Caddy (HTTPS) | 80/443 | ✅ |
| Vision прокси | 8900 | ✅ bg |
| Vision + Mistral | 8901 | ✅ bg |
| Роутер | 8002 | ✅ systemd |
| zina2-router | 8003 | ✅ systemd |
| Hermes Studio | 8648 | ✅ |
