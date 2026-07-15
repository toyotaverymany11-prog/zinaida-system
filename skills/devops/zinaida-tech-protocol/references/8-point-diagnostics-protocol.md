# 8-точечный протокол полной диагностики системы (v3 — 13.07.2026)

**ПЕРВООЧЕРЕДНО:** выполнить `python3 /opt/zinaida/scripts/tech_diagnostic.py` — скрипт v2 проверяет все 8 зон автоматически.

**Если скрипт не работает или нужна ручная глубокая проверка** — каждую зону ниже.

---

## 1. Сервисы — 10 проверок

```bash
# Список всех zina-сервисов (полная энумерация, не grep!)
ls /etc/systemd/system/*.service 2>/dev/null | xargs basename -a | sed 's/\.service$//' | sort -u | while read srv; do
  act=$(systemctl is-active $srv 2>/dev/null)
  ena=$(systemctl is-enabled $srv 2>/dev/null)
  printf "%-45s active=%-8s enabled=%-10s\n" "$srv" "$act" "$ena"
done

# Health-эндпоинты
for port in 8002 8003 8005 8901; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$port/health 2>/dev/null)
  echo "port $port → $code"
done

# Redis через порт
echo "Redis $(ss -tlnp | grep 6379 | grep -c 127.0.0.1 >/dev/null && echo '✅ localhost' || echo '⚠️ NOT localhost')"

# Systemd для не-zina сервисов
for svc in caddy hermes-gateway rclone-onedrive; do
  echo "$svc: $(systemctl is-active $svc 2>/dev/null || echo 'not found')"
done

# Таймеры — не забыть! Сервис может быть inactive, но таймер активен
systemctl list-timers --all --no-legend | grep -E "curator|backup|zinaida"
```

## 2. Сеть

```bash
# Внешний IP
curl -s https://api.ipify.org?format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('ip','?'))"

# DuckDNS доступен?
curl -s -o /dev/null -w "%{http_code}" https://zinadchdp.duckdns.org/health 2>/dev/null

# SSL сертификат (дней до истечения)
python3 -c "
import ssl, socket
ctx = ssl.create_default_context()
with socket.create_connection(('zinadchdp.duckdns.org', 443), timeout=5) as sock:
    with ctx.wrap_socket(sock, server_hostname='zinadchdp.duckdns.org') as ssock:
        cert = ssock.getpeercert()
        from datetime import datetime as dt
        expiry = dt.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        print(f'SSL: {(expiry - dt.now()).days} days left')
"

# DNS жив?
python3 -c "import socket; socket.getaddrinfo('google.com', 80); print('DNS OK')"
```

## 3. Система

```bash
df -h /                                  # диск <75%
df -i /                                  # inodes <80%
free -h                                  # RAM, swap
nproc                                    # кол-во ядер
uptime                                   # load avg (норма < cores*1.5)
ps aux | awk '{print $8}' | grep -c Z    # zombie процессы (должно быть 0)
cat /proc/sys/fs/file-nr                 # file descriptors (первые цифры — открытые)
```

## 4. Docker

```bash
docker info --format 'Daemon {{.ServerVersion}}' 2>/dev/null || echo 'Docker DEAD'

# Контейнеры
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

# Проверка: n8n — какой образ?
docker inspect n8n --format '{{.Config.Image}} {{.Config.Cmd}} {{.Size}}' 2>/dev/null
# Настоящий n8n: n8nio/n8n, размер >1GB, CMD не sleep
# Фейковый (подмена): alpine, ~12-13MB, CMD=['sleep','infinity']

# Проверка: Redis на localhost?
ss -tlnp | grep 6379

# Образы
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'

# Docker-proxy порты (маскирует порт под слушающий)
ss -tlnp | grep docker-proxy
```

## 5. Провайдеры

```bash
# DeepSeek через 8003
curl -s -w '\n%{http_code}' -X POST http://127.0.0.1:8003/v1/chat/completions \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"ok"}],"max_tokens":5}' \
  -H 'Content-Type: application/json' | tail -1

# Mistral через 8002 (FREE-FIRST)
curl -s -w '\n%{http_code}' -X POST http://127.0.0.1:8002/v1/chat/completions \
  -d '{"model":"mistral-large-latest","messages":[{"role":"user","content":"ok"}],"max_tokens":5}' \
  -H 'Content-Type: application/json' | tail -1

# GitHub Models через 8005
curl -s -w '\n%{http_code}' -X POST http://127.0.0.1:8005/v1/chat/completions \
  -d '{"model":"8005-github","messages":[{"role":"user","content":"ok"}],"max_tokens":5}' \
  -H 'Content-Type: application/json' | tail -1

# BrightData — DNS проверка
python3 -c "import socket; socket.getaddrinfo('api.brightdata.com', 443); print('BrightData DNS OK')"
```

## 6. Данные

```bash
# Qdrant коллекции
python3 -c "
import requests
r = requests.get('http://localhost:6333/collections', timeout=5)
cols = r.json().get('result', {}).get('collections', [])
for c in cols: print(c['name'])
print(f'Total: {len(cols)} collections')
"

# SQLite integrity
for db in /opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db /opt/zinaida/memory/smm_rag.db /opt/zinaida/memory/analytics.db; do
  echo -n "$(basename $db): "
  echo 'PRAGMA integrity_check;' | sqlite3 "$db" 2>/dev/null | head -1
done

# Hermes cron
hermes cron list 2>/dev/null

# Systemd таймеры проекта
for t in curator-weekly.timer zinaida-weekly-backup.timer; do
  echo "$t: $(systemctl is-active $t 2>/dev/null || echo 'not found')"
done
```

## 7. Безопасность

```bash
# Порты наружу (исключая docker-proxy, безопасные, studio)
ss -tlnp | awk '/0.0.0.0:/ && !/127.0.0.1/ && !/docker-proxy/' | grep -vE ':(22|80|443|53|51820|10050|8648|2222|5000|10200) '
# Если не пусто — разобраться

# SSH лазутчики
lastb 2>/dev/null | head -3

# Telegram API
python3 -c "
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(('api.telegram.org', 443))
    print('Telegram OK')
except Exception as e:
    print(f'Telegram: {e}')
s.close()
"
```

## 8. Мусор

```bash
# Dangling symlinky в systemd
find /etc/systemd/system -xtype l 2>/dev/null

# Кеши
du -sh /root/.cache/pip /root/.cache/uv /root/.cache/node-gyp 2>/dev/null

# Systemd journal
du -sh /var/log/journal 2>/dev/null
# journalctl --vacuum-size=500M если >1G

# .bak файлы
find /root/.hermes -maxdepth 2 -name '*.bak*' 2>/dev/null | wc -l
```

---

## ⚠️ НЮАНСЫ (добавлено 13.07.2026)

### docker-proxy маскирует порты
`ss -tlnp` показывает docker-proxy как слушающий порт на 0.0.0.0, хотя реально порт закрыт iptables.
**Диагностика:** строка с `docker-proxy` в users() — не опасно.

### .bak файлы в /root/.hermes — хронический мусор
Каждое обновление навыка создаёт .bak_* файл. На 13.07.2026 было 50+ файлов.
**Чистка:** `find /root/.hermes -name '*.bak*' -exec rm -f {} +`

### n8n — живучая зараза. 4 уровня воскрешения + финальное решение

У n8n есть 4 механизма воскрешения, которые могут работать одновременно:

| Уровень | Описание | Как убить |
|---------|----------|-----------|
| 1. RestartPolicy `always` | `docker rm -f` — единственный способ | `docker rm -f n8n` |
| 2. Docker Compose V2 ghost | Compose метаданные живут без compose-файла | `docker compose -p проект down` |
| 3. Daemon-level resurrection | Docker daemon восстанавливает контейнер из config.v2.json | Остановить Docker → удалить папку `/var/lib/docker/containers/<id>/` → запустить Docker |
| 4. Daemon recovers image | Даже после удаления образа и папки, daemon может перекачать слои | **Забить тег alpine-заглушкой** (единственное, что реально работает) |

**РЕШЕНИЕ (проверено 13.07.2026):**
После того как контейнер и настоящий образ удалены, алгоритм для даунтайм-резистентного убийства:

```bash
# 1. Создать alpine-заглушку под тегом n8nio/n8n:latest
docker run -d --name n8n-tmp alpine sleep 10
docker commit n8n-tmp n8nio/n8n:latest 2>/dev/null
docker rm -f n8n-tmp 2>/dev/null

# 2. Запустить контейнер ИЗ ЭТОГО образа с sleep infinity
docker run -d \
  --name n8n \
  --restart unless-stopped \
  n8nio/n8n:latest \
  sleep infinity

# 3. При следующем воскрешении (daemon-level) будет поднята заглушка, а не n8n
# Порт 5678 остаётся свободным
```

**Критическое отличие `sleep infinity` от `sleep N`:** Если CMD — `sleep 30`, контейнер умирает через 30 секунд, daemon перезапускает его (и так по кругу). `sleep infinity` не умирает — контейнер живёт вечно, не жрёт ресурсы, порт свободен.

**Проверка (заглушка vs настоящий n8n):**
```bash
docker inspect n8n --format '{{.Config.Cmd}}'  # должно быть [sleep infinity]
docker exec n8n cat /etc/os-release 2>/dev/null  # должно быть Alpine Linux
docker images n8nio/n8n --format '{{.Size}}'     # должно быть ~12-13MB
ss -tlnp | grep 5678                              # должно быть свободен
```

### Redis на 0.0.0.0 — частая ошибка Docker
По умолчанию `docker run -p 6379:6379 redis` пробрасывает Redis на внешний интерфейс.
**Фикс:** `--network host` + `redis-server --bind 127.0.0.1 --port 6379`.
Проверка: `ss -tlnp | grep 6379` → должен показывать `127.0.0.1:6379`, не `0.0.0.0:6379`.
