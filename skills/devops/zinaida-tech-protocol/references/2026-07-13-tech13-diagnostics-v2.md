# Техник 13 — Расширение диагностики до 8 зон здоровья

**Дата:** 13.07.2026
**Суть:** Полное переосмысление tech_diagnostic.py — от 7 поверхностных проверок к 8 системным зонам здоровья.

## Было (до Техник 13)
- 7 сервисов в SERVICES: роутеры 8002/8003, vision proxy, telegram-bot, qdrant port, rclone, caddy
- Только curl health и systemd is-active
- Не проверялось: Docker, Redis, сеть, провайдеры, БД, безопасность, кеши

## Стало (после Техник 13)
`python3 /opt/zinaida/scripts/tech_diagnostic.py` — 8 зон, 28+ точечных проверок:

| Зона | Компонентов | Что |
|------|-------------|-----|
| 1. Сервисы | 10 | 8002/8003/8005 + vision + TG + Qdrant + Redis + rclone + Caddy + Gateway |
| 2. Сеть | 4 | Внешний IP, DuckDNS, SSL (дни), DNS |
| 3. Система | 7 | Диск, inodes, RAM, swap, load, zombie, fd |
| 4. Docker | 4 | Daemon, контейнеры по именам (known set: qdrant/redis/n8n), n8n alert, образы |
| 5. Провайдеры | 4 | DeepSeek (через 8003), Mistral (через 8002), GitHub (через 8005), BrightData (DNS) |
| 6. Данные | 6 | Qdrant коллекции, SQLite integrity (3 БД), Hermes cron, systemd таймеры |
| 7. Безопасность | 3 | Порты наружу (исключая docker-proxy, safe_ports, studio_ports), SSH лазутчики, Telegram API TCP |
| 8. Мусор | 4 | Dangling symlinky, /root/.cache, systemd journal, .bak файлы |

## Найденные проблемы

| Проблема | Серьёзность | Фикс |
|----------|-------------|------|
| **Redis на 0.0.0.0:6379** | 🔴 Высокая | Перезапущен с `--bind 127.0.0.1` |
| **n8n жив 21 час** | ⚠️ Средняя | Фейковый alpine-образ (12.9MB, sleep infinity). Порт 5678 свободен |
| **50+ .bak файлов** (8.7M zinaida.bak) | 🟢 Низкая | Полная чистка: `find ... -name '*.bak*' -exec rm -f +` |
| **Dangling symlinky** (slepok, ubuntu-fan) | 🟢 Низкая | `find ... -lname '*/slepok*' -delete`, daemon-reload |
| **Кеш /root/.cache 3.1G** | 🟢 Низкая | Почищен electron, playwright, profiles_trash → 2.3G |

## Как работает автозапуск

При первом слове «техник» или «техника»:
1. Загружается навык `devops/zinaida-tech-protocol` v3.5.0
2. Пункт 0.1 протокола: `python3 /opt/zinaida/scripts/tech_diagnostic.py`
3. Результат показывается Олегу сводкой (✅/❌)
4. Только потом — обсуждение задачи

## Структура скрипта

- `/opt/zinaida/scripts/tech_diagnostic.py` — 29KB, ~550 строк
- 8 функций check_*() — по одной на зону
- Единая точка вывода `print_zone()` и `main()` со сводкой
- Exit code: 0 = всё зелено, 1 = есть проблемы
- Все проверки с таймаутами (3-10 сек), не блокируют друг друга

## Тесты

8 тестов пройдены (см. основной чат):
1. Скрипт запускается — ✅ все 8 зон зелёные
2. Навык v3.5.0 — ✅ автозапуск есть
3. Redis localhost — ✅
4. Dangling symlinks — ✅ 0
5. .bak — ✅ 0
6. Systemd — ✅ все 7 сервисов active
7. Роутеры — ✅ все 3 отвечают (Mistral 7.9s, DeepSeek 1.1s, GitHub 1.6s)
8. n8n — ⚠️ контейнер убит, образ-заглушка висит
