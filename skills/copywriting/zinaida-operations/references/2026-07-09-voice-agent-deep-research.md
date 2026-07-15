# Глубокое исследование голосовых агентов (09.07.2026)

## Контекст
Олег хочет: full-duplex голос (перебивать), управление сервером через агента, красивый интерфейс на iPad.
Задача: найти ГОТОВЫЙ продукт, не самодельную сборку.

## Проверенные варианты

### 1. Open WebUI (144k ★)
- **Full-duplex/barge-in:** ❌ Нет в upstream. Только half-duplex (push-to-talk).
- **Управление сервером:** ✅ Code execution, Tools, Connect Agent
- **iPad PWA:** ✅ Работает через Safari. Ограничения: таймауты при переключении приложений.
- **Голосовой режим:** Пользователи жалуются — «unusable in noisy environments», срабатывает на любой звук.
- **Реалтайм голос:** Только через форк rbb-dev (OpenAI Realtime API) — не слит upstream.
- **Вердикт:** ГОЛОС СЛАБЫЙ. Не подходит для real-time full-duplex.

**Ссылки:**
- Issue #14505 — шум и прерывания
- Issue #23832 — mute button (закрыт, не слит)
- Discussion #7993 — запрос real-time API (не поддерживается)
- Discussion #22622 — PR от rbb-dev (не слит)
- Форк: ghcr.io/rbb-dev/open-webui-realtime:latest

### 2. LiveKit Agents + Agent Starter React (5k ★ + 896 ★)
- **Full-duplex/barge-in:** ✅ WebRTC + TurnDetector + Adaptive Interruption
- **Управление сервером:** ✅ @function_tool — любой Python код (subprocess, os, ssh, docker)
- **iPad:** ✅ Адаптивный React (Next.js + shadcn/ui)
- **UI:** 5 визуализаторов (bar, grid, radial, wave, aura), кастомизация через app-config.ts
- **Проблемы:**
  - Edge TTS НЕ поддерживается как плагин — нужна кастомная обёртка
  - Feedback loop: агент слышит свой TTS на громкости >25-30%
  - Deepgram STT может быть нестабилен (#2224, #294)
  - Self-hosted LiveKit Server — нет Adaptive Interruption, latency выше Cloud
- **Вердикт:** ПОТЕНЦИАЛ ЕСТЬ, но нужно ElevenLabs TTS (плагин есть). Self-hosted хуже Cloud.

**Ссылки:**
- https://github.com/livekit-examples/agent-starter-react
- https://github.com/livekit/agents
- Issue #294 — transcription не работает
- Issue #315 — feedback loop
- Issue #2224 — Deepgram 400
- Issue #1724 — нет native custom TTS

### 3. Hermes Agent (CLI + Desktop)
- **Full-duplex/barge-in:** ❌ Только push-to-talk (Ctrl+B)
- **Управление сервером:** ✅ Лучший! 60+ инструментов. Работает headless.
- **iPad через браузер:** ❌ Голос через веб не работает (issue #20765 — WebRTC не реализован)
- **Telegram/Discord:** ✅ Голосовые сообщения транскрибируются
- **TTS:** Edge (бесплатно), ElevenLabs, OpenAI, Mistral — стриминг, предложение за предложением
- **Вердикт:** МОЩНЫЙ АГЕНТ, слабый голос. Если не нужен full-duplex — лучший выбор.

**Ссылки:**
- Дока voice mode: https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes
- Issue #35750 — запрос real-time voice
- Issue #314 — voice mode CLI
- Issue #20765 — микрофон не работает через веб

### 4. Pipecat (13.3k ★)
- **Full-duplex/barge-in:** ✅ Лучший в классе. Родной full-duplex, WebRTC, Gemini Multimodal Live
- **Управление сервером:** ❌ Чистый voice pipeline, не агент
- **iPad:** ✅ React SDK, prebuilt UI
- **Вердикт:** ЛУЧШИЙ ГОЛОС, НЕТ УПРАВЛЕНИЯ. Комбинация Pipecat + Hermes = идеал.

**Ссылки:** https://github.com/pipecat-ai/pipecat

### 5. OpenClaw
- **Full-duplex/barge-in:** ✅ (через Twilio, Gemini Realtime)
- **Управление сервером:** ⚠️ (персональный ассистент для ПК, не headless серверный)
- **iPad:** ✅ Web UI + iOS приложение
- **Вердикт:** БЛИЗКО, НО НЕ ДЛЯ УПРАВЛЕНИЯ СЕРВЕРОМ.

### 6. Open-Interpreter 01
- **Full-duplex/barge-in:** ✅ OpenAI Realtime API
- **Управление сервером:** ⚠️ (локальный ПК, не сервер)
- **iPad Web UI:** ❌ Нет
- **Вердикт:** НЕ ДЛЯ НАШЕГО СЛУЧАЯ.

## Итоговые рекомендации

### Лучшая комбинация (full-duplex + сервер)
**Pipecat (голосовой frontend, WebRTC) + Hermes Agent (backend управления сервером)**
Pipecat отдаёт голос на iPad, Hermes делает работу на сервере.

### Всё-в-одном (без постройки)
**LiveKit Agents + ElevenLabs TTS** — WebRTC, barge-in, function_tool, React UI.
Единственное: ElevenLabs платный ($5-22/мес).

### Если full-duplex не нужен
**Hermes Agent через Telegram** — транскрибирует голосовые сообщения, управляет сервером.
Минус: не real-time, надо отправлять голосовое сообщение и ждать ответ.

## Сравнительная таблица

| Инструмент | Full-duplex | Barge-in | Управление сервером | iPad браузер | Готовность |
|------------|:---:|:---:|:---:|:---:|:---:|
| **Hermes Agent** | ❌ | ❌ | ✅ Лучший | ❌ | ✅ |
| **LiveKit Agents** | ✅ | ✅ | ✅ (function_tool) | ✅ | ⚠️ (нужен ElevenLabs) |
| **Open WebUI** | ❌ | ❌ | ✅ | ✅ | ✅ (но голос слабый) |
| **Pipecat** | ✅ Лучший | ✅ | ❌ | ✅ | ✅ |
| **OpenClaw** | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Open-Interpreter 01** | ✅ | ✅ | ⚠️ | ❌ | ⚠️ |
