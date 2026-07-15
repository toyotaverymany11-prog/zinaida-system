# Архитектура голосового ассистента (исследование 10.07.2026)

## Выводы
Голосовой ввод/вывод УЖЕ встроен в Hermes Studio v0.6.27+.
Документация: https://github.com/EKKOLearnAI/hermes-studio/blob/main/docs/voice-dialogue.md

## Что есть в Hermes Studio
- Кнопка микрофона 🎤 в чате (push-to-talk)
- Браузерный Speech Recognition (без ключей)
- STT/TTS через серверные провайдеры
- Barge-in (перебивание агента)
- Настройки: Settings → Voice

## Что НЕ надо делать
- Не строить отдельные WS/WebRTC серверы — голос уже есть в интерфейсе
- Не предлагать LiveKit/Flowcat/Pipecat — они не нужны
- Не подключать ElevenLabs — заблокирован в РФ

## Что работает в РФ
| Компонент | Решение | Статус |
|-----------|---------|--------|
| STT (распознавание) | Браузерный SpeechRecognition или faster-whisper | ✅ |
| TTS (синтез) | Edge TTS (ru-RU-SvetlanaNeural) или Silero | ✅ |
| Интерфейс | Hermes Studio v0.6.28 (кнопка микрофона в чате) | ✅ |
| LLM | Роутер 8003 (тот же что в чате) | ✅ |

## Что НЕ работает
- ElevenLabs — РФ блокировка
- Linear MCP — OAuth не проходит
- LiveKit — Олег отклонил
- Flowcat — pre-1.0, Rust,CPU-heavy
