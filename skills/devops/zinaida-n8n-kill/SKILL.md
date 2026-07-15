---
name: zinaida-n8n-kill
description: "ПРОТОКОЛ УБИЙСТВА n8n. Docker daemon-level resurrection — контейнер воскресал 8 раз. Истинная причина: containerd snapshot (1.8GB) с файловой системой n8n. Решение: удалить containerd snapshot + rm -f + rmi."
version: 2.1.0
author: Zinaida
metadata:
  hermes:
    tags: [n8n, docker, resurrection, containerd]
    related_skills: [zinaida-tech-protocol]
---

# Протокол убийства n8n — истинная причина найдена (13.07.2026)

## Симптом
Контейнер n8n воскресает после ЛЮБЫХ методов. docker rm -f, rmi, остановка Docker, чистка /var/lib/docker/ — контейнер возвращается через 30-90 секунд или 30 минут.

## Истинная причина
**containerd snapshot** — Docker не сам восстанавливает контейнеры. Он использует containerd (нижний слой). containerd хранит снапшоты файловой системы образов в `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/`.

Все методы чистки Docker (/var/lib/docker/) НЕ трогали containerd. Поэтому контейнер воскресал.

**Проверка:**
```bash
find /var/lib/containerd -path "*/snapshots/*" -name "package.json" -exec grep -l '"name": "n8n"' {} \; 2>/dev/null
du -sh /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/*/ | sort -rh | head -5
# → ищи папку ~1.8GB с n8n
```

## Единственно верный протокол (утверждён Олегом 13.07.2026)

```bash
# 1. Удалить containerd снапшот (корень проблемы)
systemctl stop docker.service containerd
rm -rf /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/<ID_СНАПШОТА>/
systemctl start docker containerd

# 2. Удалить контейнер и образ
docker rm -f n8n 2>/dev/null
docker rmi n8nio/n8n:latest 2>/dev/null
docker system prune -f 2>/dev/null

# 3. Проверить
docker ps -a --filter name=n8n --format '{{.Names}}' 2>/dev/null || echo "✅ контейнера нет"
docker images | grep n8n || echo "✅ образа нет"
ss -tlnp | grep 5678 || echo "✅ порт свободен"
```

**Alpine-заглушка НЕ НУЖНА.** После удаления containerd снапшота Docker не может восстановить контейнер — нет файловой системы. Docker сам не инициирует docker pull.

## Хронология 8 попыток (13.07.2026)
Полная история: `/opt/zinaida/memory/n8n_kill_history.md`

## Если воскреснет снова
1. Проверить containerd — `find /var/lib/containerd -name "*n8n*" | head -5`
2. Если снапшот есть → удалить его
3. Если снапшота нет → искать в Docker image store / overlay2
4. `docker rm -f + rmi + prune` — достаточно

## Протокол «проверяй ещё раз» (добавлено 13.07.2026)

**Автоматическая проверка:** При первом слове «техник/техника» tech_diagnostic.py (8 зон здоровья) сам проверяет n8n. Если контейнер или образ появились — строка `n8n` покажет ❌ с деталями.

Когда Олег говорит «проверяй ещё раз» про n8n:
1. **Не говорить «чисто»** пока не прошло минимум 90 секунд без восстановления
2. **Показывать точное время жизни** — `docker ps --format '{{.Status}}'`
3. Если контейнер жив — **сказать прямо**, а не предлагать тот же метод
4. Если мёртв — **указать сколько секунд/минут прошло** без восстановления
5. **Доказать через inspect** — показать OS, CMD, размер образа

Пример правильного ответа:
```
✅ Контейнер мёртв (120 секунд без восстановления)
- docker ps -a: нет
- docker images n8nio/n8n: нет
- ss -tlnp | grep 5678: свободен
```
