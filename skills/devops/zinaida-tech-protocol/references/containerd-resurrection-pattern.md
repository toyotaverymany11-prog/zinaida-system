# Docker Container Resurrection — containerd snapshot (13.07.2026)

## Истинная причина
Docker НЕ сам восстанавливает контейнеры после `docker rm -f`. 
**containerd** (нижний слой контейнерного движка) хранит снапшоты файловых систем образов в `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/`.
Docker запрашивает у containerd слой → containerd отдаёт → Docker собирает контейнер.

Если слой жив в containerd — контейнер воскреснет из любого состояния Docker.

## Диагностика
```bash
# Найти снапшот контейнера в containerd
find /var/lib/containerd -path "*/snapshots/*" -name "package.json" -exec grep -l '"name": "<имя>"' {} \; 2>/dev/null

# Найти жирные снапшоты (кандидаты на удаление)
du -sh /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/*/ | sort -rh | head -5
```

## Фикс
```bash
# 1. Остановить Docker + containerd
systemctl stop docker.service containerd

# 2. Удалить снапшот (папку с ~1.8GB)
rm -rf /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/<ID>/

# 3. Запустить
systemctl start docker containerd

# 4. Добить контейнер и образ (если остались)
docker rm -f <имя> 2>/dev/null
docker rmi <образ> 2>/dev/null
docker system prune -f 2>/dev/null
```

**Alpine-заглушка НЕ НУЖНА.** Docker сам не инициирует `docker pull`.

## Почему не срабатывают другие методы
| Метод | Почему не работает |
|-------|-------------------|
| `docker rm -f` | daemon пересоздаёт из containerd |
| `docker update --restart=no` + rm | daemon игнорирует |
| stop Docker + чистка /var/lib/docker/containers/ | containerd не тронут |
| `docker rmi` | образ пересоздаётся из containerd слоя |
| Чистка JSON в /var/lib/docker/ | SIGSEGV (битый config.v2.json) |

## Полный кейс
n8n воскресал 8 раз подряд. Навык: `zinaida-n8n-kill`.
История: `/opt/zinaida/memory/n8n_kill_history.md`.
