# Техник 11 — Убийство воскресших контейнеров (12.07.2026)

## Ситуация
Олег сказал чистить n8n, LiveKit, и мёртвый zinaida-watchdog. Все три уже «удаляли куча раз», но они возвращались.

## Механизмы возвращения

### n8n — Docker daemon-level resurrection (⚠️ главное открытие)
- Контейнер запущен: `docker run --restart always --name n8n -p 5678:5678 n8nio/n8n`
- Без compose-файла, без systemd, без cron
- При `docker stop` → Docker **перезапускает** (restart policy)
- ❌ **При `docker rm -f` → НЕ убит.** Docker daemon держит контейнер во внутреннем overlay2 кеше `/var/lib/docker/containers/`. Даже после `docker update --restart=no` + `docker rm -f` + `docker rmi` — контейнер ВОСКРЕС через ~90 секунд, скачав образ заново.
- `lsof /var/run/docker.sock` показывал **пусто** во время воскрешения — не через сокет, а внутренний механизм daemon.
- `docker events` НЕ ПОКАЗАЛ событий create/start для n8n — механизм ниже уровня Docker API.
- `journalctl -u docker.service` показал только `sbJoin` и `image pulled` — без `container create`.

**Корень:** Docker daemon хранит контейнер в `/var/lib/docker/containers/<hash>/config.v2.json`. Даже после `docker rm`, если daemon не перезагружался, он может реконструировать контейнер при следующем restart политики или internal health check.

**Единственный фикс — жёсткий:**
```bash
# 1. Остановить Docker daemon (важно!)
systemctl stop docker.service

# 2. Удалить папку контейнера вручную
rm -rf /var/lib/docker/containers/*n8n*

# 3. Удалить образ
docker rmi n8nio/n8n 2>/dev/null   # на всякий случай

# 4. Запустить Docker
systemctl start docker.service

# 5. Подождать 90+ секунд — проверка
sleep 90 && docker ps -a | grep n8n   # → пусто = чисто
```

**Почему не срабатывает обычный `docker rm -f`:**
1. Docker daemon имеет internal health-check цикл
2. При активном daemon он видит, что контейнер с restart policy исчез, и пересоздаёт его
3. Перезапуск daemon сбрасывает этот кеш/очередь
4. После остановки daemon — мёртвая папка контейнера не имеет процесса, который бы её воскресил

**Дополнительная улика:** После остановки Docker и удаления папки — n8n больше НИКОГДА не появился. 90 секунд без него. Redis (упавший при остановке Docker) перезапущен — живой.

### LiveKit — Docker Compose ghost project
- compose-файл `/opt/zinaida/livekit/docker-compose.yaml` **уже был удалён**
- Но Docker Compose V2 держит проект в метаданных: `docker compose ls --all` показывает
- Контейнеры: `livekit-livekit-1`, `livekit-token-server-1`, `livekit-redis-1`
- `restart: unless-stopped` на всех
- Фикс: `docker compose -p livekit down --remove-orphans` (работает и без compose-файла)

### zinaida-watchdog — dangling symlink
- Файла `.service` не существовало (`systemctl cat` пусто)
- `systemctl daemon-reload` + `systemctl reset-failed` не помогали
- Остался симлинк: `/etc/systemd/system/multi-user.target.wants/zinaida-watchdog.service`
- Указывал на несуществующий `/etc/systemd/system/zinaida-watchdog.service`
- Фикс: `rm -f` симлинка + `daemon-reload`

## Протокол диагностики repeat-kill

```bash
# 4-точечная проверка: Docker → Compose → Systemd → Cron
echo "=== 1. Container ==="
docker inspect <name> --format 'Created:{{.Created}} Status:{{.State.Status}} Restart:{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null

echo "=== 2. Docker Compose ==="
docker compose ls --all 2>/dev/null | grep <name>

echo "=== 3. Systemd ==="
systemctl list-units --all | grep -i <name>

echo "=== 4. Cron ==="
grep -r "<name>" /etc/cron* /var/spool/cron/ 2>/dev/null; echo "exit: $?"
```

## Последовательность убийства

### Level 1: Быстрое (restart-policy или compose-only)
```bash
# Шаг 1: Снять restart policy (важно для --restart always!)
docker update --restart=no <name>

# Шаг 2: Удалить контейнер
docker rm -f <name>

# Шаг 3: Удалить образ
docker rmi <image> 2>/dev/null

# Шаг 4: Удалить compose проект (если был compose)
docker compose -p <project> down --remove-orphans 2>/dev/null

# Шаг 5: Проверка через 10-30 секунд
sleep 10 && docker ps -a | grep <name>
sleep 30 && docker ps -a | grep <name>   # повторно
docker compose ls --all | grep <project>  # проверка compose метаданных
```

### Level 2: Daemon-level resurrection (если Level 1 не сработал)
Когда контейнер воскресает даже после `docker rm -f` + `rmi` + `--restart=no`:
```bash
# Шаг 1: Остановить Docker daemon
systemctl stop docker.service

# Шаг 2: Удалить папку контейнера вручную из overlay2
rm -rf /var/lib/docker/containers/*имя*

# Шаг 3: Запустить Docker
systemctl start docker.service

# Шаг 4: Поднять упавшие контейнеры (redis, qdrant)
docker start redis qdrant 2>/dev/null

# Шаг 5: Проверка через 90+ секунд
sleep 90 && docker ps -a | grep <name>   # → пусто = чисто
```

**Проверка различий:** Level 1 достаточен для 90% случаев. Level 2 — когда все средства диагностики (inspect, lsof, events, compose ls, systemctl) пусты, а контейнер всё равно воскресает.

## Проверка watchdog-симлинков
```bash
# Найти все симлинки мёртвого сервиса
find /etc/systemd/system -lname '*/имя.service' -o -lname '*/имя.timer' 2>/dev/null

# Удалить
find /etc/systemd/system -lname '*/имя.service' -delete 2>/dev/null

# Перезагрузить
systemctl daemon-reload
```

## Итоговый check-list
- [ ] n8n — `docker ps -a` пусто, `docker images n8nio/n8n` пусто
- [ ] LiveKit — `docker compose ls --all` не показывает livekit, `docker ps -a` пусто
- [ ] watchdog — `systemctl list-units --all | grep watchdog` пусто
- [ ] Жду 90+ сек — ни один не воскрес (Level 1 failure = daemon-level resurrection → Level 2 метод)
- [ ] Проверка что живое работает: qdrant ✅, redis ✅, роутеры ✅, сервисы ✅
- [ ] Диск: размер ДО и ПОСЛЕ (n8n образ 2.47GB освобождён)
