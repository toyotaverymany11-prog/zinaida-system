# LiveKit Voice Agent — Финальное развёртывание (09.07.2026)

## Состояние на конец сессии

### ✅ Запущено и работает

| Компонент | Статус | Порт | Примечание |
|-----------|--------|------|------------|
| LiveKit Server | ✅ Docker | 7880 | `livekit-livekit-1` (host network) |
| Redis | ✅ Docker | 6379 | `redis` (был до этой сессии) |
| Token Server | ✅ Docker | 7890 | Отдаёт JWT токены |
| Web UI | ✅ Caddy | 443 → /zinaida/ | Красивый интерфейс с аватаром, визуализатором, микрофоном |
| Python Agent | ✅ Запущен | — | Deepgram STT → 8003 → Silero TTS |
| Caddy WS Proxy | ✅ Есть | /livekit-ws/ → :7880 | Проксирует WebRTC через HTTPS |

### 🖥️ UI (https://zinadchdp.duckdns.org/zinaida/)

Современный тёмный интерфейс:
- Аватар Зинаиды (zinaida_01.jpg) по центру, grayscale в idle, цветной при разговоре
- Canvas с аудиовизуализатором (волновая форма в реальном времени)
- Кнопка микрофона с пульсацией
- Статусы: НАЖМИ ДЛЯ РАЗГОВОРА / СЛУШАЮ / ДУМАЮ / ОТВЕЧАЮ
- Транскрипт: показывает что сказал пользователь и что ответила Зинаида
- Прерывание: нажать микрофон во время ответа → перебивает
- LiveKit WebRTC подключение

### 🤖 Агент (zinaida_agent.py)

Стек:
1. `livekit-agents` (Python) — фреймворк
2. `livekit-plugins-deepgram` — STT, модель nova-2, русский язык
3. Прямые HTTP вызовы к роутеру 8003 (DeepSeek Flash→Pro→V3)
4. Fallback на 8002 (OpenRouter) при ошибке 8003
5. Silero v5 TTS (kseniya, 48kHz) — локально, бесплатно
6. Hermes API (:8001) — для команд «сделай...», «запусти...»
7. Контекст разговора: история до 20 сообщений

**Прерывание речи:** клиент шлёт `{"type": "interrupt"}` через DataChannel → агент прекращает генерацию/воспроизведение.

**Распознавание команд:** если текст содержит «сделай», «выполни», «запусти», «создай», «напиши», «открой», «проверь» → идёт к Hermes API, иначе к роутеру 8003.

## Файлы

| Файл | Назначение |
|------|------------|
| `/opt/zinaida/livekit/docker-compose.yaml` | LiveKit server + token server |
| `/opt/zinaida/livekit/livekit.yaml` | Конфиг LiveKit (ключи: apidevkey/apidevsecret) |
| `/opt/zinaida/livekit/token_server.py` | JWT токен-сервер на :7890 |
| `/opt/zinaida/livekit/zinaida_agent.py` | Python-агент (Deepgram → 8003 → Silero) |
| `/opt/zinaida/livekit/zinaida-ui/index.html` | Веб-интерфейс (Canvas + LiveKit SDK) |
| `/opt/zinaida/livekit/zinaida-ui/zinaida_06_serious.jpg` | Аватар (копия zinaida_01.jpg) |

## Как запустить заново

```bash
# 1. Redis (если нет)
docker run -d --name redis --network host redis:alpine

# 2. LiveKit + Token Server
cd /opt/zinaida/livekit && docker compose up -d

# 3. Агент
cd /opt/zinaida/livekit && python3 zinaida_agent.py start

# 4. UI (уже через Caddy на /zinaida/)
# Открыть https://zinadchdp.duckdns.org/zinaida/
```

## Caddy (уже настроено)

```caddy
handle_path /livekit-ws/* {
    reverse_proxy localhost:7880
}
handle_path /zinaida/* {
    root * /opt/zinaida/livekit/zinaida-ui
    file_server
}
handle_path /zinaida-token/* {
    uri strip_prefix /zinaida-token
    reverse_proxy localhost:7890
}
```

## Deepgram ключ

```
Ключ: 2c917fa7c4a00dfba0e3b91097f0ab8891e0512f
Проект: 5d540801-1a34-4ad1-97a3-136cf8382e10
Бесплатный кредит: $200
Модель: nova-2 (язык: ru)
Сохранён в: sysadmin/SECRETS.md, /opt/zinaida/config/secrets.env
```

## Известные проблемы

1. **Silero TTS официально deprecated** в livekit-agents v2.0. Будет заменён на Kokoro или ElevenLabs.
2. **ElevenLabs заблокирован для РФ.** Альтернатива: Kokoro (бесплатный open-source TTS, Docker).
3. **Голос Ксении (Silero)** Олег считает несерьёзным. Нужен более качественный голос.
