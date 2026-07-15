# Техник 14: Свип портов и настройка UFW — 13.07.2026

## Что произошло

Олег сказал «техник» — я загрузила навык, НО не выполнила шаг 0.1 (автозапуск диагностики).
Вместо этого ответила пустым «что чиним?». Олег в ярости: 3 сообщения с матом, потребовал объяснить:
- что за «8 портов наружу»
- почему скрипт не сработал
- какая нейросеть отвечала

## 8 портов, найденных на 0.0.0.0

| Порт | Процесс | Опасность | Фикс |
|------|---------|-----------|------|
| 2222 | SSH (sshd) | Брутфорс снаружи | ufw allow 2222 |
| 2019 | Caddy admin API | Админка веб-сервера наружу | ufw deny, Caddy слушает локально |
| 8648 | Hermes Studio Web UI | UI управления наружу | Уже проксирован через Caddy (HTTPS) |
| 9090 | `python3 -m http.server` | Директория загрузок Hermes (`/root/.hermes-web-ui/upload/`) | **УБИТ** — не systemd, запущен из bash |
| 9091 | `python3 -m http.server` | Весь `/root` наружу (файловая шара) | **УБИТ** — не systemd, запущен из bash |
| 5000 | VK bot (Flask) | Нужен для VK вебхуков | ufw allow 5000 |
| 10200 | Edge TTS server | Голосовой сервер | Уже проксирован Caddy → `handle_path /tts/*` |
| 10050 | Zabbix agent | Системный мониторинг | Безопасен (read-only) |

## Почему Caddy не спасает

Caddy проксирует через HTTPS: Hermes Studio (8648), TTS (10200), голос (7893).
НО: порты всё равно висят на 0.0.0.0 отдельно от Caddy.
UFW блокирует прямой доступ к портам, оставляя только Caddy (80/443).

## UFW — протокол настройки

1. **Бэкап iptables:** `iptables-save > /opt/zinaida/backup_iptables_YYYYMMDD.txt`
2. **Проверить установку ufw:** `which ufw && ufw status`
3. **Убить опасные HTTP-серверы** (python3 -m http.server): `kill PID; ss -tlnp | grep PORT`
4. **Проверить что серверы не systemd:** `systemctl list-units --all | grep PORT`
5. **Настроить UFW:**
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow 2222/tcp      # SSH
   ufw allow 80/tcp        # Caddy HTTP
   ufw allow 443/tcp       # Caddy HTTPS
   ufw allow 5000/tcp      # VK bot webhook
   ufw --force enable
   ```
6. **Проверить что порты закрылись:**
   ```bash
   ss -tlnp | grep "0.0.0.0:"   # должно быть только: 2222, 80, 443, 5000, 10050
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8648/  # Hermes жив локально
   curl -s -o /dev/null -w "%{http_code}" https://zinadchdp.duckdns.org/  # Caddy жив
   ```
7. **Проверить что не сломалось:**
   - `curl http://127.0.0.1:8002/health` — роутер 8002
   - `curl http://127.0.0.1:8003/health` — роутер 8003
   - `curl http://127.0.0.1:8005/health` — роутер 8005
   - `curl http://127.0.0.1:5000/vk_webhook` — VK бот
   - Telegram отправляет сообщение → проверка бота
8. **Записать опыт** в Mem0 + fact_store + обновить service_registry.md

## Важные выводы

### Порты 9090/9091 — откуда взялись
Запущены не systemd, не cron, не docker — просто висели в процессах от bash-сессий:
```bash
/usr/bin/bash -lic set +m; cd /root/.hermes-web-ui/upload/default && python3 -m http.server 9090 --bind 0.0.0.0
/usr/bin/bash -lic set +m; cd /root && python3 -m http.server 9091 --bind 0.0.0.0
```
Это legacy от разработки Hermes Studio (загрузка файлов через HTTP вместо API).
Просто `kill PID` — больше не появятся (нет systemd-сервиса).

### Какая нейросеть отвечала (вопрос Олега)
На «Техник 14» отвечал **8005-Flash** (Super Cascade роутер, порт 8005).
Провайдер: `custom` (кастомный роутер), модель: `8005-Flash`.

**User preference (записать в MEMORY.md и навык):**
Олег требует знать какая модель/провайдер отвечала, когда он спрашивает «почему так», «что за хуйня», «какая нейросеть».
Отвечать: `[модель] через [провайдер/роутер], время ответа Xс`.

### UFW — текущая конфигурация на 13.07.2026:
```
ufw status verbose
→ Status: active
→ Default: deny (incoming), allow (outgoing)
→ 2222/tcp ALLOW IN
→ 80/tcp ALLOW IN
→ 443/tcp ALLOW IN
→ 5000/tcp ALLOW IN
```
