# LiveKit + Voice UI Setup (2026-07-09, обновлено 2026-07-09 финальное)

## Работающая конфигурация

```
HTTPS (Caddy на 80/443 -> 7891)
  ↓
React UI (/opt/zinaida/livekit/zinaida-ui/) — порт 7891
  ↓ (получает JWT токен)
Token Server (/opt/zinaida/livekit/token_server.py) — порт 7890
  ↓ (подключается через WSS)
Caddy proxy (/livekit-ws/ → localhost:7880)
  ↓
LiveKit Server (Docker) — порт 7880/7881/7882
  ↓
Redis (Docker) — порт 6379
```

## Домен

```
zinadchdp.duckdns.org → Caddy (80/443)
```

Доступ через HTTPS: `https://zinadchdp.duckdns.org/zinaida/`

### Caddy routes для LiveKit

```caddy
# Токен-сервер
handle_path /zinaida-token/* {
    uri strip_prefix /zinaida-token
    reverse_proxy localhost:7890
}

# LiveKit WebSocket (для WSS подключения)
handle_path /livekit-ws/* {
    reverse_proxy localhost:7880
}

# UI (файловый сервер)
handle_path /zinaida/* {
    root * /opt/zinaida/livekit/zinaida-ui
    file_server
}
```

Файл конфига: `/etc/caddy/Caddyfile`

## Компоненты

**LiveKit Server:**
```bash
docker run -d --name livekit --network host livekit/livekit-server \
  --dev --keys "zinaida-key: zinaida-secret-key" \
  --redis-host "127.0.0.1:6379" --bind "0.0.0.0"
```
Порты: 7880 (HTTP API), 7881 (TCP WebRTC), 7882+ (UDP WebRTC)
Важно: для iPad нужен `--bind "0.0.0.0"` и HTTPS через Caddy.

**Token Server:** `/opt/zinaida/livekit/token_server.py` (порт 7890)
- Генерирует JWT для подключения клиента к комнате
- URL LiveKit в токене: `https://zinadchdp.duckdns.org/livekit-ws` (через Caddy, а не прямой WS)
- Ключ/секрет: `zinaida-key` / `zinaida-secret-key`

**React UI:** `/opt/zinaida/livekit/zinaida-ui/index.html`
- LiveKit Client SDK через CDN (esm.sh/livekit-client)
- Аватар: zinaida_06_serious.jpg (выбран Олегом)
- Пульсирующая сфера + кнопка микрофона
- Состояния: idle/listening/thinking/speaking
- Константы:
  ```javascript
  const LIVEKIT_URL = 'wss://zinadchdp.duckdns.org/livekit-ws';
  const TOKEN_URL = '/zinaida-token/?room=zinaida-room';
  const AVATAR_URL = '/zinaida/zinaida_06_serious.jpg';
  ```

**Silero TTS (голос Зинаиды):**
- Модель: v5_ru (48kHz, качество в 2 раза лучше v4)
- Голос: **kseniya** (женский, выбран Олегом 09.07.2026)
- Альтернативы: baya, xenia (женские), aidar, eugene (мужские)
- Локально на сервере, бесплатно, без интернета
- Установка: `pip install silero torch torchaudio scipy`
- Генерация: 48kHz, ~0.3 сек на 100 символов
- Первый запуск: `trust_repo=True` (скачивает 139MB модель)
- Тестовые файлы: `/opt/zinaida/livekit/zinaida-ui/test_silero_*.wav`
- Полное демо: `/opt/zinaida/livekit/zinaida-ui/zinaida_full_demo.wav`

**Deepgram STT (распознавание речи Олега):**
- Ключ: 2c917fa7c4a00dfba0e3b91097f0ab8891e0512f
- Проект: 5d540801-1a34-4ad1-97a3-136cf8382e10
- Модель: nova-2, язык: ru
- Бесплатный кредит: $200
- Сохранён: `/opt/zinaida/config/secrets.env` + `/opt/zinaida/design/sysadmin/SECRETS.md`

## Что не доделано

1. **Голосовой агент** — полный пайплайн Deepgram → Router → Silero TTS не написан
2. **Tencent API для Telegram** — периодически не отвечает (ConnectTimeout)
3. **LiveKit голосовой агент на Python** — код написан, но не протестирован

## Проблемы при установке

1. `@livekit/agents-ui` не найден в npm registry — используется livekit-client напрямую через CDN
2. LiveKit config YAML имеет специфические имена полей — проще запускать через флаги `--dev`
3. WebRTC требует HTTPS на iPad — решено через Caddy (Let's Encrypt)
4. Telegram API периодически недоступен с сервера (ConnectTimeout) — это сетевая проблема хостинга
5. Эндпоинт /rtc на LiveKit не отвечает на HTTP — только WebSocket (нормально, не ошибка)
