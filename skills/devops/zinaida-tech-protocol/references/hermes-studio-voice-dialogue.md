# Hermes Studio Voice Dialogue — Built-in голосовой ввод/вывод

**Источник:** https://github.com/EKKOLearnAI/hermes-studio/blob/main/docs/voice-dialogue.md

## Что есть в v0.6.27+

- Кнопка микрофона в чате (рядом с полем ввода)
- STT: браузерный SpeechRecognition (Chrome/Safari, без ключей) или серверный провайдер
- TTS: браузерный SpeechSynthesis или серверный провайдер
- Barge-in: при начале новой записи останавливает воспроизведение ответа агента
- Полудуплекс (record → transcribe → edit → send)
- Настройки провайдеров в Settings → Voice

## Чего нет
- Wake-word (всегда слушать)
- Full-duplex (одновременный разговор)
- Телефония
- Фоновый режим

## Как включить/проверить
1. Обновить Hermes Studio: `npm update -g hermes-web-ui && systemctl restart hermes-web-ui`
2. Ctrl+Shift+R в браузере (hard refresh, чтоб сбросить кэш)
3. Проверить поле ввода чата — должна быть иконка микрофона
4. Settings → Voice → настроить STT (браузер или сервер) и TTS (браузер или сервер)

## Для голоса как у Алисы (wake-word, full-duplex)
Использовать отдельный WebSocket-сервер — `/opt/zinaida/voice_assistant/` (порт 7893).
URL: https://zinadchdp.duckdns.org/voice-chat/
Стек: Whisper (STT) → Роутер 8003 → Edge TTS/Silero.
Wake-word: openWakeWord (CPU, <100ms, open-source) — не внедрён.
