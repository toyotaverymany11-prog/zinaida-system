# MOA катастрофа, UFW порты, DeepSeek billing — 13.07.2026

## 1. MOA (Mixture of Agents) — КАТЕГОРИЧЕСКИЙ ЗАПРЕТ

### Что случилось
13.07.2026 Зинаида включила MOA на всех роутерах (параллельный запуск DeepSeek Flash + Pro на каждый запрос). Каждый запрос платил ×2. Олег заметил на platform.deepseek.com/usage, что деньги уходят быстрее.

### Почему заметил
Весь день работал с планшета, 18 диалоговых сессий через 8003 (чистый DeepSeek Pro). Каждая с большим контекстом. MOA удваивал стоимость каждого ответа. 36 вызовов DeepSeek вместо 18, $0.03-0.05 vs $0.02 за день.

### Решение
MOA вырезан из zina2_router.py. Заменён на последовательный вызов: сначала Flash (дешёвый, $0.27/M токенов), если упал — Pro ($1.42/M).

### Везде заблокировано (13 точек):
- Mem0 — записан запрет
- fact_store #49 — запрет с тегом
- MEMORY.md — перезаписано
- SOUL.md — раздел запрета
- AGENTS.md — добавлено
- system-guarantee-protocol skill — триггер MOA
- zina2_router.py — MOA удалён из кода
- shared_memory/updates_log.md — записано

### Ключевой LESSON
Любая функция, влияющая на расходы пользователя — ОБЯЗАТЕЛЬНО согласовать. Показать цену. Не включать молча.

### Диагностика расходов DeepSeek (команды)
```bash
# Сколько вызовов DeepSeek через 8003
journalctl -u zina2-router.service --no-pager --since "2026-07-13 00:00" | grep -c "model=deepseek"
journalctl -u zina2-router.service --no-pager --since "2026-07-13 00:00" | grep -oP "model=\S+" | sort | uniq -c

# Сколько вызовов DeepSeek через 8005 (каскад)
journalctl -u zina2-router-8005.service --no-pager --since "2026-07-13 00:00" | grep -c "DEEPSEEK\|deepseek"
journalctl -u zina2-router-8005.service --no-pager --since "2026-07-13 00:00" | grep "DEEPSEEK" | grep -oP "\((flash|pro)\)" | sort | uniq -c

# Сколько fallback на DeepSeek из 8002
journalctl -u zinaida-router.service --no-pager --since "2026-07-13 00:00" | grep -c "DeepSeek"

# Общее количество за день
total=$(journalctl -u zina2-router-8005.service --no-pager --since "2026-07-13 00:00" | grep -c "DEEPSEEK"; journalctl -u zina2-router.service --no-pager --since "2026-07-13 00:00" | grep -c "model=deepseek"; journalctl -u zinaida-router.service --no-pager --since "2026-07-13 00:00" | grep -c "DeepSeek")

# Проверка баланса DeepSeek (ключ невалидный — authentication_error)
curl -s "https://api.deepseek.com/user/balance" -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```

---

## 2. UFW — закрытие портов

### Ситуация
Диагностика показала 8 портов наружу. Среди них:
- **9090** — `python3 -m http.server` на `/root/.hermes-web-ui/upload/` (папка загрузок)
- **9091** — `python3 -m http.server` на `/root/` (ВЕСЬ КОРЕНЬ наружу!)
- **8648** — Hermes Studio Web UI напрямую
- **2019** — Caddy admin API
- **5000** — VK bot (нужен для вебхуков)
- **10200** — голосовой сервер edge_tts
- **2222** — SSH
- **10050** — Zabbix агент (системный)

### Что сделано
```bash
# Убить HTTP-шары
kill 607200 624868  # PID 9090 и 9091

# UFW
ufw --force disable && ufw --force reset
ufw default deny incoming && ufw default allow outgoing
ufw allow 2222/tcp comment "SSH"
ufw allow 80/tcp comment "Caddy HTTP"
ufw allow 443/tcp comment "Caddy HTTPS"
ufw allow 5000/tcp comment "VK bot webhook"
ufw --force enable
```

### Что осталось наружу
| Порт | Сервис | Комментарий |
|------|--------|-------------|
| 2222 | SSH | Нужен |
| 80 | Caddy HTTP | Редирект на HTTPS |
| 443 | Caddy HTTPS | Основной вход |
| 5000 | VK bot | Вебхуки от VK |

### Что ушло на localhost (закрыто)
- 8002, 8003, 8005 — роутеры
- 8648 — Hermes Studio (только через Caddy HTTPS)
- 8642 — Hermes Gateway
- 2019 — Caddy admin
- 6379 — Redis
- 6333/6334 — Qdrant
- 8900/8901 — Ollama/vision proxy
- 9090/9091 — HTTP-шары (убиты)
- 10200 — голосовой сервер
