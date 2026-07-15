# Voice assistant quick reference

## Текущее работающее решение
**Свой WS сервер** — порт 7893, Python aiohttp.
- Whisper STT (локально, CPU)
- Роутер 8003
- Edge TTS (или Silero 7892)

URL: https://zinadchdp.duckdns.org/voice-chat/

## Что не предлагать
- LiveKit (отклонён)
- Flowcat (pre-1.0 Rust, нет бинарников)
- ElevenLabs (блокировка РФ)
- Pipecat (требует GPU)

## Что попробовать (Yandex SpeechKit)
Лучший русский голос. Нужен API ключ (Yandex Cloud, бесплатный грант 1000₽ на 60 дней).
TTS: ~0.21₽/запрос (API v3).
Подключается через HTTP API, не OAuth.
Замена Edge TTS в server.py на Yandex SpeechKit.
Олег в курсе, хочет попробовать но ключ пока не получил.
