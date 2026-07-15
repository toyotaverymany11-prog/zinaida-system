# LiveKit + Caddy + WebSocket — итоговая схема (09.07.2026)

## Компоненты

```
Браузер (iPad) → Caddy (порты 80/443, SSL) → Backend
```

### Caddy routes (zinadchdp.duckdns.org)

| Путь | Назначение | Бэкенд |
|------|-----------|--------|
| `/zinaida/*` | UI (аватар, сфера, кнопка) | файлы из `/opt/zinaida/livekit/zinaida-ui/` |
| `/zinaida-ws*` | WebSocket для текстовых запросов | localhost:7892 |
| `/zinaida-token/*` | JWT токен для LiveKit | localhost:7890 |
| `/livekit-ws*` | WebSocket для LiveKit | localhost:7880 |
| `/` | Hermes Studio (основной) | localhost:8648 |

### WebSocket сервер (zinaida_wss.py)

**Порт:** 7892
**Файл:** `/opt/zinaida/livekit/zinaida_wss.py`

Протокол: браузер шлёт JSON `{"type":"text","text":"..."}`, сервер отвечает `{"type":"thinking"}` и `{"type":"response","text":"..."}`.

Запуск: `cd /opt/zinaida/livekit && python3 zinaida_wss.py`

### LiveKit (WebRTC транспорт)

- Docker образ: livekit/livekit-server
- Порты: 7880 (HTTP/WS), 7881 (TCP), 7882 (UDP медиа)
- Бинд: 0.0.0.0 (исправлено)
- Ключи: zinaida-key / zinaida-secret-key

Запуск:
```bash
docker run -d --name livekit --network host livekit/livekit-server --dev --keys "zinaida-key: zinaida-secret-key" --redis-host "127.0.0.1:6379" --bind "0.0.0.0"
```

### Токен-сервер (token_server.py)

**Порт:** 7890
**Файл:** `/opt/zinaida/livekit/token_server.py`
Генерирует JWT для LiveKit.
Доступен через Caddy: `/zinaida-token/`

### UI (index.html)

- Путь: `/opt/zinaida/livekit/zinaida-ui/index.html`
- Доступ: https://zinadchdp.duckdns.org/zinaida/
- Аватар: zinaida_06_serious.jpg
- Чистый JS (без CDN/importmap)
- WebSocket напрямую к серверу

## Ключевые решения

**WebRTC без HTTPS не работает на iPad** → Caddy с Let's Encrypt.
**LiveKit на localhost — не подключиться** → --bind 0.0.0.0.
**CDN заблокированы в РФ** → никаких importmap, чистый JS.
**Telegram API недоступен** → слать результат в ответе чата.

## Что осталось

- [ ] Голосовой пайплайн: Deepgram STT → Router → Silero TTS
- [ ] Переключение с текстового WS на голосовой LiveKit
- [ ] Systemd сервисы для всех компонентов
