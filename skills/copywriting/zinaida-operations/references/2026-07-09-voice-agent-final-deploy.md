# Voice Agent Final v2.0 — LiveKit + Agent Starter React + Edge TTS

## Дата: 2026-07-09

## Состав стека (проверено, работает)

| Компонент | Технология | Статус |
|-----------|-----------|--------|
| Голосовой UI | LiveKit Agent Starter React (Next.js + shadcn/ui) | ✅ Работает |
| Сервер | LiveKit 1.13.3 (Docker, host network) | ✅ Работает |
| Redis | redis:alpine (Docker, port 6379) | ✅ Работает |
| Токен сервер | Python (livekit-api, port 7890) | ✅ Работает |
| Агент | livekit-agents 1.6.5 + livekit-plugins-deepgram 1.6.5 | ✅ Работает |
| STT | Deepgram Nova-2 (русский) | ✅ Ключ есть |
| TTS | Edge TTS (ru-RU-SvetlanaNeural), Microsoft Neural | ✅ Бесплатно, без ключа |
| LLM | Роутер 8003 (DeepSeek, fallback 8002) | ✅ Работает |
| Команды | Hermes API (:8001) | ✅ Работает |
| Caddy | HTTPS прокси | ✅ Работает |

## Пути и порты

- UI: `/opt/zinaida/livekit/ui-react/` (Next.js, порт 3030)
- Caddy URL: `/voice/` → `localhost:3030`
- Caddy WebSocket: `/livekit-ws/` → `localhost:7880`
- LiveKit: порт 7880 (WebRTC WS), 7881 (TCP)
- Агент: `/opt/zinaida/livekit/zinaida_agent.py`
- Токен сервер: `/opt/zinaida/livekit/token_server.py` (порт 7890)
- Docker Compose: `/opt/zinaida/livekit/docker-compose.yaml`
- Конфиг LiveKit: `/opt/zinaida/livekit/livekit.yaml`

## Старт стека

```bash
# 1. Docker (LiveKit + Token Server)
cd /opt/zinaida/livekit && docker compose up -d

# 2. Next.js UI
cd /opt/zinaida/livekit/ui-react
NODE_ENV=production npx next start -p 3030 &

# 3. Агент (требует LIVEKIT_URL)
cd /opt/zinaida/livekit
LIVEKIT_URL=wss://zinadchdp.duckdns.org/livekit-ws \
LIVEKIT_API_KEY=apidevkey \
LIVEKIT_API_SECRET=apidevsecret \
python3 zinaida_agent.py start &

# 4. Скрипт всего сразу
bash /opt/zinaida/livekit/start_stack.sh
```

## Кастомизация React UI

Файл: `/opt/zinaida/livekit/ui-react/app-config.ts`

Настройки Зинаиды:
- companyName: 'Зинаида'
- pageTitle: 'Зинаида — голосовой агент'
- logo: '/zinaida_06_serious.jpg' (аватар)
- startButtonText: 'Начать разговор'
- visualizer: 'radial' (32 бара)
- accentDark: '#00ff96'

Удалены:
- Ссылка на livekit.io из хедера
- Ссылка "Voice AI quickstart" снизу
- Лого LiveKit (заменён на аватар)

## Убранный мусор

- `/opt/zinaida/livekit/zinaida-ui/` — старый самописный кругляшок
- Старый токен сервер (заменён на версию с wss URL)

## Известные ограничения

1. Агент использует `cli.run_app(WorkerOptions(...))` — это стандартный LiveKit Agent worker
2. Edge TTS возвращает MP3 — нужна конвертация в PCM через ffmpeg
3. Deepgram ключ жёстко прописан в коде агента — вынести в .env при деплое
4. Агент не имеет systemd сервиса — только ручной запуск
