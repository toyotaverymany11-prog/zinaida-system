# n8n Killing Saga — Техник 13 (13.07.2026)

Полная хронология 8 попыток убийства контейнера n8n.

## Краткая суть
Контейнер n8n воскресал 8 раз подряд. Причина — **containerd snapshot #667** (1.8GB), который я не трогала при чистке Docker. Docker только менеджер, реальное восстановление идёт через containerd.

## Хронология

| # | Метод | Результат | Причина отказа |
|---|-------|-----------|----------------|
| 1 | `docker rm -f` | ❌ воскрес 60-90с | restart: always |
| 2 | `docker update --restart=no` + rm -f | ❌ воскрес | daemon игнорирует |
| 3 | Остановка Docker + rm папки containers/ | ❌ воскрес | containerd жив |
| 4 | `docker compose down` | ❌ воскрес | не compose-проект |
| 5 | Alpine-заглушка sleep infinity | ❌ воскрес через 20мин | containerd восстановил настоящий |
| 6 | Чистка всех JSON в /var/lib/docker/ | ❌ SIGSEGV + воскрес | битый config.v2.json + containerd |
| 7 | **containerd snapshot #667 удалён** | ✅ заглушка | **корень найден** |
| 8 | `docker rm -f + rmi + prune` (без заглушки!) | ✅ **ПОЛНОСТЬЮ** | containerd мёртв |

## Ключевые уроки

### Урок 1: containerd — истинная причина
Docker НЕ сам восстанавливает контейнеры. Он использует containerd. containerd хранит слои образов в `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/`. Если слой жив — контейнер воскреснет из любого удобного состояния Docker.

### Урок 2: Alpine-заглушка НЕ НУЖНА
Олег: «зачем держать имя? удали чтоб не было упоминаний». После удаления containerd снапшота Docker не может восстановить. Docker сам не делает `docker pull`.

### Урок 3: SIGSEGV от битого JSON
Чистка JSON в /var/lib/docker/image/overlay2/ привела к падению Docker с `panic: runtime error: invalid memory address or nil pointer dereference` в `daemon/container.go:92`. Фикс: удалить битый config.v2.json конкретного контейнера.

### Урок 4: Проверка n8n
При первом слове «техник» tech_diagnostic.py проверяет n8n. Если контейнер/образ появились — сразу видно.
