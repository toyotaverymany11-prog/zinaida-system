# Протокол верификации удаления контейнера (Техник 11 — 12.07.2026)

## Ситуация
Олег говорит «проверяй ещё раз» — не верит что контейнер действительно убит.
Причина: было 5 заходов на n8n. Он воскресал 4 раза разными механизмами.

## Протокол

### Шаг 1: Диагностика «кто держит контейнер» (одна команда)
```bash
echo "=== Container ==="
docker inspect <name> --format 'Created:{{.Created}} RestartPolicy:{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null || echo "(уже мёртв)"
echo "=== Compose ==="
docker compose ls --all 2>/dev/null | grep -i <name> || echo "(нет)"
echo "=== Systemd ==="
systemctl list-units --all | grep -i <name> || echo "(нет)"
echo "=== Cron ==="
grep -r "<name>" /etc/cron* /var/spool/cron/ 2>/dev/null; echo "(exit: $?)"
```

### Шаг 2: Метод убийства (выбрать по результатам Шага 1)
| Результат Шага 1 | Метод |
|---|---|
| RestartPolicy: always | `docker rm -f <name>` **плюс** остановка Docker |
| RestartPolicy: unless-stopped | `docker rm -f <name>` |
| Compose проект есть | `docker compose -p <project> down --remove-orphans` |
| Systemd сервис есть | `systemctl stop <name> && systemctl disable <name>` |

**ЕСЛИ контейнер воскресает после `rm -f` и ни compose/systemd/cron не найдены:**  
→ **Docker daemon internal resurrection.** Требуется полная остановка Docker:
```bash
systemctl stop docker.service docker.socket
rm -rf /var/lib/docker/containers/*<name>*
systemctl start docker.service
# Поднять упавшие контейнеры
docker start redis qdrant 2>/dev/null
```

### Шаг 3: Верификация с временным интервалом
Удаление не считается завершённым, пока не прошло 90 секунд без восстановления.

```bash
# Проверить сразу
docker ps -a --filter name=<name> --format '{{.Names}}' || echo "НЕТ"
# wait 30
sleep 30 && docker ps -a --filter name=<name> --format '{{.Names}}' || echo "НЕТ"
# wait 60 more
sleep 60 && docker ps -a --filter name=<name> --format '{{.Names}}' || echo "НЕТ"
```

**Критерий готовности:** все 3 проверки показали пусто.

### Шаг 4: Если Олег сказал «проверяй ещё раз»
1. **НЕ говорить** «я уже проверила, чисто» — он не поверит
2. **Запустить полный цикл верификации заново** (все 4 шага)
3. **Показать каждый чек** в таблице:
   ```
   | Проверка | Результат |
   |----------|-----------|
   | docker ps -a — контейнер | ✅ НЕТ |
   | docker images — образ | ✅ НЕТ |
   | ss -tlnp — порт | ✅ СВОБОДЕН |
   | systemd — сервис | ✅ НЕТ |
   | Через 30 секунд | ✅ НЕТ |
   | Через 60 секунд | ✅ НЕТ |
   | Через 90 секунд | ✅ НЕТ |
   ```

### Шаг 5: Что НЕ делать
- **НЕ говорить** «удалила» когда только `docker stop` или `docker kill` — контейнер с `restart: always` вернётся
- **НЕ говорить** «удалила» не проверив RestartPolicy — если `always`, нужен особый метод
- **НЕ проверять** только `docker ps -a` один раз — контейнер может воскреснуть через 30-90 секунд
- **НЕ удалять** образ перед удалением контейнера — это не влияет, образ скачается заново
- **НЕ полагаться** только на `docker compose ls` — проект может быть ghost (файла нет, но метаданные живы)

## Пример (Техник 11 — n8n)
```
Проверка 1 (11:33): контейнер есть, rm -f → через 30 секунд воскрес
Проверка 2 (11:46): rm -f + rmi → через 90 секунд воскрес (pull заново 2.47GB)
Проверка 3 (11:56): rm -f + rmi + update --restart=no → через 90 секунд воскрес
Проверка 4 (12:01): Остановка Docker + удаление папки + старт → через 90 секунд НЕТ
Проверка 5 (12:27): через 4 минуты — всё ещё НЕТ ✅
```
