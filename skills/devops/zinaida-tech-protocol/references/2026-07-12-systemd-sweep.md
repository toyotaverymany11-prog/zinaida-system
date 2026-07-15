# Systemd sweep — 12.07.2026 (Техник 8)

## Контекст
Олег: «не понял что за мёртвые системы что за грузы мёртвые блядь давай разберёмся»
Полная энумерация через `ls /etc/systemd/system/*.service` выявила **42 systemd-юнита**.

## Протокол аудита мёртвых сервисов

### Шаг 1: Полная энумерация
```bash
# НЕ systemctl list-units --all (пропускает timer-only сервисы)
ls /etc/systemd/system/zinaida*.service /etc/systemd/system/zina2*.service
    /etc/systemd/system/vkbot.service /etc/systemd/system/obushenie*.service
```

### Шаг 2: Проверить каждый
```bash
for srv in $(ls /etc/systemd/system/zinaida*.service | xargs basename -a | sed 's/\.service$//'); do
    printf "%-45s active=%-10s enabled=%-10s\n" \
        "$srv" "$(systemctl is-active $srv)" "$(systemctl is-enabled $srv)"
done
```

### Шаг 3: Проверить таймеры
```bash
# Таймер может быть active+enabled, а сервис inactive 
# → сервис реально запускается по таймеру!
systemctl list-timers --all | grep zinaida
```

### Шаг 4: Проверить файлы на диске
Что делать с каждым inactive сервисом:
```bash
systemctl cat service-name | grep ExecStart=
# → проверка: файл существует? ls -la /path/to/script.py
```
Если файла нет на диске → 100% мёртв.

### Шаг 5: Проверить последний запуск
```bash
systemctl show -p ActiveEnterTimestamp service-name
# → Если n/a или >30 дней назад → мёртв
```

## Результат чистки 12.07.2026

| Метрика | До | После |
|---------|----|-------|
| Всего systemd-юнитов | 42 | 8 |
| Активных | 7 | 7 |
| Мёртвых | 35 | 0 |
| Таймеров active+enabled | 6 | 1 (weekly-backup) |

### Что удалено
- **33 .service файла** — старая автономия, мёртвые API, старые роутеры
- **14 .timer файлов** — self-reflection (15 мин), skill-registrar (2 мин), memory-consolidator (daily), sync (5 мин) и другие
- **1 zinaida.service** — старый роутер-клон

### Что осталось (7 active)
`obushenie-mounts`, `vkbot`, `zina2-router` (8003), `zina2-router-8005` (8005),
`zinaida-core` (sleep infinity — legacy compat), `zinaida-router` (8002), `zinaida-telegram-bot`

### Ключевые находки аудита
1. **Не верить systemctl list-units --all** — 19 showed, 42 existed
2. **Таймеры не показываются в service list** — 6 extra found via `list-timers`
3. **zinaida-core — живой?** — `sleep infinity`. Работает, но ничего не делает. Legacy compat заглушка.
4. **Файлов нет на диске** — dashboard, toolgateway: systemd запускает несуществующие файлы
