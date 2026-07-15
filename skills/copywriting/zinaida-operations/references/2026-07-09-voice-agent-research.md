# Голосовой агент: исследование готовых решений (09.07.2026)

## Контекст
Олег хочет голосовое управление контент-заводом: говорит в iPad → агент на сервере выполняет команды → отвечает голосом. На экране — красивый современный UI (не «самописный кругляшок»).

## Требования
- Веб-интерфейс (iPad через браузер, PWA)
- Голосовой ввод (нажать кнопку → говорить → STT)
- Подключение к любому OpenAI-compatible LLM (наш Hermes API :8001 / роутер :8003)
- Голосовой ответ (TTS, качественный, не Silero)
- Красивый современный дизайн
- Минимальная установка (Docker предпочтительнее)
- Бесплатно / open-source

## ТОП-3 решения

### 1. Open WebUI (144,416 ★)
- GitHub: https://github.com/open-webui/open-webui
- Лицензия: MIT
- Установка: docker run -d -p 3000:8080 ghcr.io/open-webui/open-webui:main
- Web UI: ✅ PWA, адаптивный, тёмная тема, как ChatGPT
- STT: Whisper (локально), OpenAI Whisper API, Deepgram, Azure
- TTS: OpenAI TTS, Azure, ElevenLabs, Kokoro, Browser WebAPI
- LLM: Любой OpenAI-compatible (Ollama, vLLM, OpenRouter, Hermes API)
- Русский язык: ✅ i18n, голосовой ввод/вывод
- PWA на iPad: ✅
- Сложность: 1 команда Docker
- Адаптация под Hermes: В админ-панели указать OpenAI URL = http://127.0.0.1:8001

### 2. LiveKit Agents (~5,000 ★)
- GitHub framework: https://github.com/livekit/agents
- GitHub React UI: https://github.com/livekit-examples/agent-starter-react (896 ★)
- Лицензия: Apache-2.0
- Web UI: shadcn/ui, 5 стилей аудиовизуализаторов (bar, grid, radial, wave, aura)
- STT: 20+ провайдеров (Deepgram, OpenAI, Whisper, AssemblyAI)
- TTS: 20+ провайдеров (ElevenLabs, Cartesia, OpenAI, Azure)
- LLM: 20+ провайдеров (OpenAI, Anthropic, Gemini, Ollama, Groq, Mistral)
- Особенности: WebRTC, прерывание речи, multi-agent, MCP инструменты
- Сложность: нужен LiveKit сервер + Python + React
- Адаптация под Hermes: LLM как OpenAI-compatible, TTS/STT через API

### 3. Voice Chat AI (~1,000 ★)
- GitHub: https://github.com/bigsk1/voice-chat-ai
- Лицензия: MIT
- Установка: docker pull bigsk1/voice-chat-ai:latest
- Web UI: FastAPI интерфейс, дизайн скромный
- LLM: OpenAI, Anthropic, xAI, Ollama
- TTS: ElevenLabs, OpenAI, Kokoro (локально), Spark-TTS
- STT: OpenAI Whisper API, локальный Faster Whisper
- Сложность: низкая

## STT (Speech-to-Text)

| Сервис | Тип | Цена | Качество русского |
| Deepgram | Облачный API | $200 кредит есть | Отличное (nova-2 модель) |
| OpenAI Whisper API | Облачный API | $0.006/мин | Хорошее |
| Whisper (локальный) | Локально, без GPU | Бесплатно | Хорошее, медленно на CPU |
| Vosk | Локально | Бесплатно | Среднее |

Deepgram ключ: 2c917fa7c4a00dfba0e3b91097f0ab8891e0512f
Deepgram проект: 5d540801-1a34-4ad1-97a3-136cf8382e10

## TTS (Text-to-Speech)

| Сервис | Тип | Цена | Качество русского |
| ElevenLabs | Облачный API | Бесплатный tier 10k символов/мес | Отличное, естественная интонация |
| OpenAI TTS | Облачный API | $0.015/1K символов | Отличное |
| Silero v5 (Ксения) | Локально | Бесплатно | Хорошее, но «несерьёзное» |
| Kokoro | Docker | Бесплатно | Хорошее, open-source |
| ChatTTS | Локально | Бесплатно | Отличное, выразительное |

ВАЖНО: ElevenLabs заблокирован для РФ. SaluteSpeech — российская альтернатива.

## Вывод

Open WebUI — оптимальный выбор:
1. 1 Docker команда
2. PWA на iPad
3. Голос из коробки
4. Подключается к Hermes API
5. 144k звёзд, активное сообщество

GPU не нужен — всё на текущем сервере (4 CPU, 8GB RAM).

## Что готово на сервере
- ✅ Docker установлен и работает
- ✅ Caddy с HTTPS на zinadchdp.duckdns.org
- ✅ Hermes API (:8001)
- ✅ Роутеры: 8002 (OpenRouter), 8003 (DeepSeek)
- ✅ Silero TTS (установлен)
- ✅ Deepgram ключ
- ✅ Аватар: /opt/zinaida/zinaida_passport/generated/zinaida_01.jpg
- ❌ Open WebUI — не установлен
