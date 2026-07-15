# Кейс: zhivoy-slepok — мёртвый таймер, дёргающий несуществующий скрипт

**Дата:** 12.07.2026, Техник 9
**Симптом:** `systemctl list-units --type=service --state=failed` показывает `zhivoy-slepok.service` failed
**Источник:** Системный таймер `zhivoy-slepok.timer` (active+enabled, 3:00 каждое утро)

## Детали

**ExecStart:** `/opt/zinaida/scripts/update_zhivoy_slepok.py` — файл НЕ СУЩЕСТВУЕТ с 9 июля 2026

**Лог:**
```
Jul 09 06:00:01 python3[2996402]: can't open file 'update_zhivoy_slepok.py': [Errno 2] No such file or directory
Jul 10 06:00:01 python3[3315457]: can't open file 'update_zhivoy_slepok.py': [Errno 2] No such file or directory
...
Jul 12 03:00:00 python3[4065370]: can't open file 'update_zhivoy_slepok.py': [Errno 2] No such file or directory
```

Таймер дёргал мёртвый сервис 4 дня подряд. Каждый раз `status=2/INVALIDARGUMENT`. Ожидал реакции Олега — не было. Я увидела при диагностике и оставила в таблице — тоже ошибка.

## Протокол убийства мёртвого таймера (подтверждён Олегом: «надо выключать нахуй»)

```bash
# 1. Стопнуть и отключить таймер
systemctl stop zhivoy-slepok.timer
systemctl disable zhivoy-slepok.timer

# 2. Удалить файлы (systemctl mask НЕ работает на реальных файлах!)
rm -f /etc/systemd/system/zhivoy-slepok.timer
rm -f /etc/systemd/system/zhivoy-slepok.service

# 3. Перезагрузить systemd
systemctl daemon-reload

# 4. Сбросить failed-статус
systemctl reset-failed zhivoy-slepok.service 2>/dev/null

# 5. Проверка — пусто
systemctl list-units --all | grep zhivoy
# → (ничего)
```

## Причина dead-таймера

Файл `update_zhivoy_slepok.py` существовал на момент создания сервиса, потом был удалён (вероятно при чистке неиспользуемых скриптов). Таймер остался — система не удаляет таймеры автоматически при пропаже скрипта.

## Проверка мёртвых таймеров (предотвращение)

При любой диагностике:
```bash
# Все failed сервисы
systemctl list-units --type=service --state=failed

# Для каждого failed — проверить ExecStart
systemctl cat сервис.service | grep ExecStart | head -1

# Существует ли файл?
ls -la /path/from/ExecStart 2>/dev/null || echo "ФАЙЛ НЕ НАЙДЕН"
```
