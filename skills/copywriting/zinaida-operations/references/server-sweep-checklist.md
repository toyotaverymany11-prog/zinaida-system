# Системный пробег по серверу — единый протокол

## Когда использовать

- Олег говорит «пробегись по серверу», «проверь всё», «посмотри нет ли проблем»
- После крупного обновления инфраструктуры
- Раз в неделю в рамках профилактики

## Протокол (8 шагов, параллельно где возможно)

### Шаг 0: Docker-compose файлы — источники авто-восстановления (ДОБАВЛЕНО 2026-07-10)

**Зачем:** Docker Compose V2 автоматически пересоздаёт контейнеры из docker-compose.yml.
Если контейнер имеет `restart: always` и описан в compose-файле — после `docker rm` он восстанавливается
за секунды. Именно так n8n возвращался каждый день.

```bash
# Найти все docker-compose файлы (не node_modules)
find /opt /root -maxdepth 4 -name "docker-compose*" -not -path "*/node_modules/*" 2>/dev/null

# Проверить каждый файл на наличие нежелательных сервисов
grep -A2 "^\s\+[a-z]" /opt/openclaw/docker-compose.yml 2>/dev/null
```

**Красные флаги:** любые compose-файлы с сервисами, которые не должны работать (n8n, portainer, watchtower, и т.д.)

**Если контейнер восстанавливается после удаления:**
1. **СНАЧАЛА** удалить compose-файл: `rm -f <путь>/docker-compose.yml`
2. Потом остановить контейнер: `docker stop <name> && docker rm <name>`
3. Удалить volume: `docker volume rm <name>_data`
4. Удалить образ: `docker rmi <image>`
5. Проверить порт: `ss -tlnp | grep <port>` — должен быть пуст
6. Подождать 2 минуты — проверить что не восстал

**Порядок критичен:** если удалить контейнер, не удалив compose-файл — Compose пересоздаст контейнер немедленно.

### Шаг 1: Docker-контейнеры — не висит ли лишнее

```bash
docker ps --format "{{.Names}} {{.Image}} {{.Ports}}"
```

**Проверить:**
- n8n — ДОЛЖЕН быть удалён (+ npm global). Если висит: `docker stop n8n && docker rm n8n && npm uninstall -g n8n`
- Неожиданные контейнеры на портах 5678 (n8n), 3000 (unexpected), 8080 (unexpected)
- Легитимные: livekit-*, redis, n8n (удалён), другие согласованные

### Шаг 2: Система — диск, память, нагрузка

```bash
df -h /                    # свободное место
free -h                    # RAM + swap
uptime                     # аптайм, нагрузка
du -h --max-depth=2 / 2>/dev/null | sort -rh | head -20
```

**Красные флаги:** диск >85%, RAM used >6GB, swap >1GB, нагрузка >4.

**Типовые пожиратели диска (сессия 2026-07-10):**
- `/opt/zinaida.BAK.*/` — бэкапы до 19GB → `rm -rf`
- `/root/.hermes.BAK.*/` — до 500MB → `rm -rf`
- `/root/.npm/_cacache` + `/root/.npm/_npx` — до 3.4GB → `npm cache clean --force && rm -rf /root/.npm/_npx`
- `/opt/zinaida/sandbox/*.bak*` + `*.tmp*` — десятки-сотни файлов → `find ... -exec rm -rf {} +`

### Шаг 3: Все systemd сервисы — статус

```bash
systemctl list-units --type=service --state=running --no-legend | grep -E "zinaida|hermes|rclone|telegram|livekit|caddy|vision"
systemctl list-units --type=service --state=failed --no-legend
```

**Проверить:**
- Все ключевые сервисы active running: роутер, gateway, Caddy, TG-бот, rclone mount, vision proxy
- **rclone-onedrive.service** — enabled (иначе не поднимется после ребута). Если disabled: `systemctl enable rclone-onedrive.service`
- **zinaida-sync.service** — timer enabled и активен (bisync каждые 5 мин)
- **zinaida-unified-diagnostic.service** — если failed, проверить ExecStart путь (типовая проблема: файл перенесли из sandbox/ в memory/)

### Шаг 4: OneDrive/rclone — монтирование и синхронизация

```bash
mount | grep -i onedrive                                 # смонтирована?
systemctl status rclone-onedrive.service --no-pager -l    # mount жив?
systemctl status zinaida-sync.timer --no-pager -l         # bisync таймер?
journalctl -u rclone-onedrive.service --no-pager -n 15    # ошибки в логах
```

**Типовые ошибки в логах mount:** `itemNotFound`, `too many errors`, `vfs cache: failed to download` — это признаки проблем с OneDrive файлами (обычно временные SQLite .db-shm файлы, их можно игнорировать).

**Проверка bisync:** последний лог должен быть `Deactivated successfully` с exit code 0.

### Шаг 5: Дубликаты проектов и мусор

```bash
# Дублирующиеся бэкапы
du -sh /opt/zinaida.BAK* /root/.hermes.BAK* 2>/dev/null | sort -rh

# Мусорные bak/tmp файлы в sandbox
find /opt/zinaida/sandbox -maxdepth 5 \( -name "*.bak*" -o -name "*.tmp*" \) 2>/dev/null | wc -l

# Code-мусор в проектах
ls /opt/zinaida/projects/code_*.py 2>/dev/null | wc -l

# Двойные папки проектов
echo "--- /opt/zinaida/projects/ ---" && ls /opt/zinaida/projects/ 2>/dev/null
echo "--- /opt/zinaida/inbox/PROJECTS/ ---" && ls /opt/zinaida/inbox/PROJECTS/ 2>/dev/null
```

**Важно:** `/opt/zinaida/inbox/PROJECTS/` — старая папка внутри OneDrive mount, содержит настоящие данные (phases.db, adapters). `/opt/zinaida/projects/` — новая, содержит только README. Они НЕ дубли, но путают.

### Шаг 6: Проверка systemd путей — не разъехались ли

```bash
# Найти .service файлы, где ExecStart ссылается на несуществующий путь
grep -rn "ExecStart" /etc/systemd/system/ | grep -E "zinaida|vision" | while IFS=: read -r file line rest; do
  path=$(echo "$rest" | grep -oP '/\S+\.py' | head -1)
  [ -n "$path" ] && [ ! -f "$path" ] && echo "⚠️ $file: $path — ФАЙЛ НЕ НАЙДЕН"
done
```

**Типовая проблема:** `zinaida-unified-diagnostic.service` часто ссылается на `/opt/zinaida/sandbox/unified_diagnostic.py`, а реальный файл — в `/opt/zinaida/memory/`. Фикс: `sed -i 's|/sandbox/|/memory/|g' /etc/systemd/system/zinaida-unified-diagnostic.service && systemctl daemon-reload`

### Шаг 7: Проверка таймеров — все ли активны

```bash
systemctl list-timers --no-pager | grep -E "zinaida|curator"
```

**Ключевые таймеры:**
- `zinaida-sync.timer` — bisync каждые 5 мин
- `zinaida-unified-diagnostic.timer` — раз в час (часто падает, см. шаг 5)
- `curator-weekly.timer` — воскресенье
- `zinaida-skill-registrar.timer` — каждые 2 мин

### Шаг 7: Node.js — версии и дубли (сессия 2026-07-10)

```bash
node --version && which node
dpkg -l nodejs* 2>/dev/null | grep "^ii"
ls /usr/local/n/versions/node/ 2>/dev/null
du -sh /root/.npm/ 2>/dev/null
```

**Проверить:**
- Есть ли два node: `/usr/bin/node` (dpkg) и `/usr/local/bin/node` (n) — если да, удалить dpkg: `apt remove -y nodejs`
- npm cache: если >500MB → `npm cache clean --force && rm -rf /root/.npm/_npx /root/.npm/_cacache`
- Node 8 (n8n runtime): не должно быть вообще — ни в n, ни в dpkg

### Шаг 8: Финальный замер — диск после чистки

```bash
df -h /          # должно быть >60% свободно после чистки бэкапов
```

## Формат ответа Олегу

```
[ЗИНАИДА] Сводка по пробегу:

### ⚠️ ПРОБЛЕМЫ (список с приоритетами)
1. ... [что нашла]
2. ... [что нашла]

### ✅ НОРМАЛЬНО
1. ... [что работает]
2. ... [что работает]

### ЧТО СДЕЛАЛА
1. ... [конкретные фиксы]
2. ...

### ЧТО НУЖНО ОТ ТЕБЯ (если нужно)
1. ...
```

Без преамбул и размышлений. Только факты.
