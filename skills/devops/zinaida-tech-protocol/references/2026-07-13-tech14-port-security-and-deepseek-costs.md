# Техник 14 — Port Security + DeepSeek Costs (13.07.2026)

## 1. Обнаруженные опасные порты

| Порт | Процесс | Опасность |
|------|---------|-----------|
| `0.0.0.0:9090` | `python3 -m http.server 9090` | Папка `/root/.hermes-web-ui/upload/default/` — все загрузки Hermes Studio наружу |
| `0.0.0.0:9091` | `python3 -m http.server 9091` | Весь `/root/` наружу — полный доступ к корню системы |
| `0.0.0.0:8648` | Hermes Studio (Node.js) | Интерфейс управления без аутентификации напрямую |
| `0.0.0.0:2019` | Caddy admin API | API управления веб-сервером |
| `0.0.0.0:2222` | SSH | Брутфорс |
| `0.0.0.0:10200` | edge_tts_server.py | Голосовой сервер |
| `0.0.0.0:10050` | Zabbix agent | Системный мониторинг (менее опасно) |

## 2. UFW настройка

```bash
# Бэкап
iptables-save > /opt/zinaida/backup_iptables_YYYYMMDD.txt

# Настройка UFW
ufw --force disable && ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp comment "SSH"
ufw allow 80/tcp comment "Caddy HTTP"
ufw allow 443/tcp comment "Caddy HTTPS"
ufw allow 5000/tcp comment "VK bot webhook"   # если VK вебхуки
ufw --force enable
ufw status verbose

# Проверка
ss -tlnp | grep "0.0.0.0:"    # должно остаться только разрешённое
curl https://zinadchdp.duckdns.org -o /dev/null -w "%{http_code}"  # → 200
```

**Проверка что сервисы живы:** после включения UFW проверить Caddy, Hermes Studio (через HTTPS), Telegram-бот, VK.

## 3. DeepSeek расходы — анализ ускоренного списания

### 13.07 — Олег заметил что деньги уходят быстрее

**Факты:**
- Сегодня ≈20 вызовов DeepSeek через все роутеры (в деньгах ≈$0.02)
- 8003 (чистый DeepSeek): 0 прямых вызовов за день
- 8005 (Super Cascade): 18 вызовов DeepSeek (GitHub падает с 413 → каскад)
- 8002 (FREE-FIRST): 2 fallback на DeepSeek

**Причины ускорения (3 версии):**

1. **MOA × 2** — включён 13.07 во все роутеры. Каждый запрос = 2 параллельных вызова DeepSeek (Flash + Pro) вместо 1. Удваивает стоимость.

2. **GitHub 413 → платный DeepSeek** — в логах 8005: GitHub возвращает `tokens_limit_reached` (413) на большие контексты, 6 попыток за 3 сек → каскад на DeepSeek. Бесплатный путь не работает → платная модель.

3. **Маленький остаток** — если на счету $5, каждый доллар визуально заметен. $0.50 за день = 10% баланса.

**Что делать:**
- Отключить MOA на 8003 (вернуть single call) — снизит расход в 2×
- Поднять лимит токенов GitHub или отключить его из каскада
- Проверить баланс DeepSeek: `curl -s "https://api.deepseek.com/user/balance" -H "Authorization: Bearer $KEY"`

### Диагностика DeepSeek

```bash
# Сколько запросов к DeepSeek сегодня
journalctl -u zina2-router-8005.service --since "2026-07-13 00:00" | grep -c "DEEPSEEK.*OK"
journalctl -u zinaida-router.service --since "2026-07-13 00:00" | grep -c "fallback\|DEEPSEEK"

# GitHub 413 — бесполезные попытки
journalctl -u zina2-router-8005.service --since "2026-07-13 00:00" | grep "413"

# Баланс DeepSeek
source /opt/zinaida/meta_agent/.env
curl -s "https://api.deepseek.com/user/balance" -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```
