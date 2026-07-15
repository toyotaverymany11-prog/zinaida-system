# Фейковый образ — блокировка бессмертного Docker контейнера

**Дата:** 12.07.2026 (Техник 11)
**Проблема:** n8n восстанавливался после `docker rm -f`, `docker update --restart=no`, `docker rmi`, остановки Docker + удаления папки.

## Когда применять

- Контейнер живёт своей жизнью — воскресает через 60-90 секунд
- `docker compose ls` — пусто
- `systemctl` — пусто
- `cron` — пусто
- `lsof /var/run/docker.sock` — только dockerd
- `docker events` — молчит

## Метод

### Шаг 1: Убить и заменить образ

```bash
# Убить контейнер и удалить настоящий образ
docker rm -f n8n 2>/dev/null
docker rmi n8nio/n8n 2>/dev/null

# Создать фейковый образ на основе alpine
docker run --name n8n-blocker alpine:latest echo "blocked" 2>/dev/null
docker commit n8n-blocker n8nio/n8n:latest 2>/dev/null
docker rm n8n-blocker 2>/dev/null
```

### Шаг 2: Запустить заглушку

```bash
# Запустить с тем же именем и портами, что и оригинал
docker run --name n8n --restart=always -d -p 5678:5678 n8nio/n8n:latest sleep infinity
```

### Шаг 3: Верификация

```bash
# Проверка ОС — должна быть Alpine Linux, НЕ n8n
docker exec n8n cat /etc/os-release  # → NAME="Alpine Linux"

# Проверка команды — sleep infinity, НЕ n8n entrypoint
docker ps --filter name=n8n --format '{{.Command}}'  # → "sleep infinity"

# Проверка размера — ~9-12MB, НЕ 2+ GB
docker images n8nio/n8n --format '{{.Size}}'  # → 12.9MB (не 2.09GB)

# Проверка порта — может висеть docker-proxy
ss -tlnp | grep 5678
# Если занят — убить proxy
fuser -k 5678/tcp 2>/dev/null
```

### Шаг 4: Ожидание

Подождать 90-120 секунд. Если образ не заменился на настоящий — контейнер заблокирован навсегда.

```bash
sleep 90
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Size}}\t{{.Status}}'
# n8n должен быть: alpine 12.9MB, Up ~2min (не 2.09GB, не настоящий n8n)
docker images n8nio/n8n --format '{{.Size}}'  # → 12.9MB
```

## Почему это работает

Docker daemon может восстанавливать контейнеры через внутренний механизм (ниже уровня API), но он восстанавливает **образ по тому же имени тега**. Если тег `n8nio/n8n:latest` указывает на alpine-заглушку — будет восстановлена заглушка, а не настоящий n8n.

Docker НЕ делает `docker pull` автоматически — только если образ удалён. А он не удалён — он заменён на alpine.

## Побочные эффекты

- docker-proxy может висеть на порту 5678 — убивать `fuser -k`
- Образ занимает ~9MB (вместо 2GB) — это плюс
- Если когда-нибудь понадобится настоящий n8n — `docker rm -f n8n && docker rmi n8nio/n8n && docker pull n8nio/n8n && docker run ...`
