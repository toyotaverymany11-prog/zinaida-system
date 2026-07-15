# Telegram Bot Architecture — @DCHP_Shtab_bot

## Архитектура
- Бот: `/opt/zinaida/telegram_bot/bot.py`
- Сервис: `zinaida-telegram-bot.service` (systemd, всегда запущен)
- Notify-утилита: `/opt/zinaida/telegram_bot/notify.py` — для отправки уведомлений

## Подключение к LLM
- **URL:** `http://127.0.0.1:8002/v1` (Zinaida-Router, НЕ gateway на 8642)
- **Model:** `Zinaida-Router`
- **Auth:** `Authorization: Bearer dummy-key`

**НЕ использовать port 8642 (gateway)** — gateway требует OAuth/portal-аутентификацию и возвращает 401.

## Приём медиа
Бот принимает: текст, фото, видео, голосовые, документы, аудио.
Файлы сохраняются в `/opt/zinaida/telegram_bot/media/`.

## История ошибок
- **401 Invalid API key (Jul 9):** Бот стучался на gateway (8642), который требовал OAuth-ключ. Решение: переключить на Zinaida-Router (8002) с dummy-key.
- **401 (Jul 8):** Бот стучался на 8644, а gateway на 8642. Решение: исправить порт.
- **Таймауты при отправке:** Telegram API иногда не отвечает (ConnectTimeout). Повтор через notify.py решает.

## Уведомления (notify.py)
```bash
python3 /opt/zinaida/telegram_bot/notify.py "текст"
```
- Вызывать только если не могу ответить в чате Hermes Studio.
- Не дублировать ответы из чата.
