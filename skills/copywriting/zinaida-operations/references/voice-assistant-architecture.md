# Голосовой ассистент Zinaida — архитектура (10.07.2026)

## Решение
Свой WS сервер на Python (aiohttp). Не LiveKit. Не Flowcat (pre-1.0, Rust, сырой).

## Архитектура
```
iPad (браузер)                  Сервер
┌─────────────────┐             ┌──────────────────────────────┐
│ index.html       │ WebSocket  │ server.py (порт 7893)         │
│ getUserMedia →   │◄─────────► │ ↓                             │
│ PCM audio chunks  │           │ Whisper STT (faster-whisper)  │
│                  │            │ → Роутер 8003 (наш LLM)      │
│ play response    │            │ → Edge TTS / Silero          │
│ audio           │            │ → возврат аудио               │
└─────────────────┘             └──────────────────────────────┘
```

## Компоненты
- **Сервер:** `/opt/zinaida/voice_assistant/server.py` — Python aiohttp
- **Страница:** `/opt/zinaida/voice_assistant/index.html`
- **Caddy:** `/voice-chat/` → proxy 7893, `/voice-ws/` → proxy 7893
- **URL:** https://zinadchdp.duckdns.org/voice-chat/
- **STT:** faster-whisper tiny (локально, CPU, int8)
- **LLM:** роутер 8003 (Zina2-Router, DeepSeek)
- **TTS:** Edge TTS ru-RU-SvetlanaNeural (или Silero как fallback)

## Режим работы
- Как Алиса — открыл страницу, нажал «Старт», говоришь
- VAD по энергии сигнала (порог 300, тишина ~0.5 сек = конец фразы)
- Barge-in — перебиваешь агента, он замолкает
- Нет кнопок во время разговора

## Ограничения
- Edge TTS — среднее качество русского голоса (Олег сказал «так себе»)
- Silero TTS лучше, уже стоит на порту 7892
- Yandex SpeechKit — лучший русский голос, но нужен API ключ (0.21₽/запрос, бесплатный грант 1000₽)
- На CPU Whisper tiny обрабатывает ~1-2 сек речи за 0.5-1 сек

## Что не использовать
- LiveKit — ❌ Олег отклонил (глючный, сложный)
- Flowcat — ❌ pre-1.0 Rust, нет готовых бинарников
- Pipecat — ❌ требует GPU
- ElevenLabs — ❌ блокировка РФ
