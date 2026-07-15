# Сессия 2026-07-09 — WOW-UI, LiveKit, Silero TTS, Caddy

## LiveKit + UI + Caddy (готовая инфраструктура)

### Что работает

| Компонент | Статус | Порт/URL |
|-----------|--------|----------|
| LiveKit сервер (Docker) | ✅ | ws://127.0.0.1:7880 (локально) |
| Redis (Docker) | ✅ | 127.0.0.1:6379 |
| Токен-сервер (Python) | ✅ | 127.0.0.1:7890 |
| React UI (аватар + сфера + микрофон) | ✅ | http://127.0.0.1:7891 |
| HTTPS (Caddy) | ✅ | https://zinadchdp.duckdns.org |
| UI через HTTPS | ✅ | https://zinadchdp.duckdns.org/zinaida/ |
| Токен через HTTPS | ✅ | https://zinadchdp.duckdns.org/zinaida-token/ |

### Запуск LiveKit

```bash
docker run -d --name livekit --network host livekit/livekit-server --dev --keys "zinaida-key: zinaida-secret-key" --redis-host "127.0.0.1:6379" --bind "127.0.0.1"
```

### Файлы

- Агент: `/opt/zinaida/livekit/zinaida_agent.py`
- Токен-сервер: `/opt/zinaida/livekit/token_server.py`
- UI: `/opt/zinaida/livekit/zinaida-ui/index.html`
- Caddyfile: `/etc/caddy/Caddyfile`

### Caddy config (HTTPS)

Домен: `zinadchdp.duckdns.org`

Пути:
- `/zinaida/*` → статика (UI) из `/opt/zinaida/livekit/zinaida-ui/`
- `/zinaida-token/*` → прокси на токен-сервер :7890
- Остальное → прокси на Hermes Studio :8648

**Проблема WebRTC:** LiveKit сервер на 127.0.0.1:7880 — WebRTC не работает через Caddy. 
Нужно либо (1) открыть порты LiveKit наружу, (2) настроить WSS прокси в Caddy, (3) поднять TURN сервер.
Пока UI виден, но голос через WebRTC с iPad не подключится.

## Silero TTS v5 — выбранный голос

**Модель:** v5_ru (скачана, сохранена в torch cache)
**Голос (выбран Олегом):** `kseniya` — женский, взрослый, уверенный
**Частота:** 48kHz
**Качество:** значительно лучше v4

Остальные голоса: baya, xenia (женские), aidar, eugene (мужские)

### Генерация

```python
import torch, scipy.io.wavfile as wav
model, _ = torch.hub.load('snakers4/silero-models', 'silero_tts',
                           language='ru', speaker='v5_ru', trust_repo=True)
model.to('cpu')
audio = model.apply_tts(text="Текст", speaker='kseniya', sample_rate=48000)
wav.write('output.wav', 48000, audio.numpy())
```

### Установка

```bash
pip install silero torch torchaudio scipy
```

### Тестовые файлы на сервере

`/opt/zinaida/livekit/zinaida-ui/test_v5_*.wav` — 5 голосов
`/opt/zinaida/livekit/zinaida-ui/zinaida_full_demo.wav` — полное демо
`/opt/zinaida/livekit/zinaida-ui/demo_post.wav` — создание поста голосом
`/opt/zinaida/livekit/zinaida-ui/demo_hello.wav` — приветствие

### LiveKit плагины

Установлены: `livekit-agents`, `livekit-plugins-deepgram`, `livekit-plugins-silero`
**Важно:** `livekit-plugins-silero` предощает только VAD (Voice Activity Detection), НЕ TTS.
TTS нужно через прямой вызов Silero модели.

## Аватар Зинаиды

**Выбран:** `zinaida_06_serious.jpg` (утверждено Олегом 09.07.2026, номер 6)
**Где:** `/opt/zinaida/zinaida_passport/generated/zinaida_06_serious.jpg`
**Скопирован в:** `/opt/zinaida/livekit/zinaida-ui/zinaida_06_serious.jpg`

## API ключи

Deepgram (STT): 2c917fa7c4a00dfba0e3b91097f0ab8891e0512f
Проект: 5d540801-1a34-4ad1-97a3-136cf8382e10

## Что не доделано (на 09.07.2026 вечер)

1. Python-агент для LiveKit — написан, но не проверен. API LiveKit Agents SDK изменился,
   нужно разобраться с `AgentSession` / `Agent` / `pipelines`.
2. WebRTC не работает через HTTPS (LiveKit на localhost).
3. Полный пайплайн: микрофон → Deepgram → роутер → Silero → динамик.
4. Telegram отправка: api.telegram.org временно недоступен с сервера (ConnectTimeout).

## Правило: проверять ссылки перед отправкой

Жёсткий урок от Олега: перед отправкой любой ссылки — проверить что она открывается.
Использовать `browser_navigate()` для проверки. Если ERR — найти правильный URL.
Конкретный пример: отправила studio.sber.ru — не открывается (ERR_NAME_NOT_RESOLVED).
Правильный: https://developers.sber.ru/studio/
