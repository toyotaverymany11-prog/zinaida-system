# Systemd Dead-Service Audit Protocol

Когда Олег ставит под сомнение «это точно мусор?» про неактивные сервисы.
НИКОГДА не гадать. Проверять каждый.

## Триггеры
- Олег: «а ты уверена?», «проверь», «давай разберёмся», «мёртвые сервисы»
- После `tech_diagnostic.py` — проверить что список сервисов не устарел
- После любого изменения/удаления сервиса — свип (см. service-deletion-sweep.md)

## Полный протокол аудита (8 шагов)

### Шаг 0: Полная энумерация — grep НЕДОСТАТОЧЕН
`systemctl list-units --type=service --all | grep zina` может ПРОПУСТИТЬ сервисы.
Причина: systemctl not-loaded units не всегда попадают в grep.

**Фикс:** Читать прямо с диска:
```bash
# Все .service файлы в директории
ls /etc/systemd/system/zinaida-*.service /etc/systemd/system/zina2-*.service 2>/dev/null
```

**Реальный кейс (12.07.2026):** grep показал ~20 сервисов, а на диске лежало **42 unit-файла**. Разница в 2x — почти половина сервисов была невидима для grep-фильтра.

### Шаг 1: Собрать все сервисы со статусом и последним запуском
```bash
# 1.1. Получить полный список с диска
for f in /etc/systemd/system/zinaida-*.service /etc/systemd/system/zina2-*.service \
         /etc/systemd/system/vkbot.service /etc/systemd/system/obushenie-mounts.service; do
  srv=$(basename "$f" .service)
  act=$(systemctl is-active "$srv" 2>/dev/null)
  ena=$(systemctl is-enabled "$srv" 2>/dev/null)
  ts=$(systemctl show -p ActiveEnterTimestamp "$srv" 2>/dev/null | cut -d= -f2-)
  printf "%-45s active=%-10s enabled=%-10s last_run=%s\n" "$srv" "$act" "$ena" "$ts"
done

# 1.2. Узнать какие из них — timers (критично!)
for t in $(ls /etc/systemd/system/zinaida-*.timer 2>/dev/null | xargs basename -a | sed 's/\.timer$//'); do
  act=$(systemctl is-active "$t.timer" 2>/dev/null)
  ena=$(systemctl is-enabled "$t.timer" 2>/dev/null)
  trig=$(systemctl show -p Triggers "$t.timer" 2>/dev/null | cut -d= -f2-)
  cal=$(systemctl show -p OnCalendar "$t.timer" 2>/dev/null | cut -d= -f2-)
  printf "TIMER %-45s active=%-10s enabled=%-10s triggers=%s cal=%s\n" "$t.timer" "$act" "$ena" "$trig" "$cal"
done
```

Ключевые поля: статус (active/inactive/not-found), дата последней активации, **наличие активного таймера**.
- **active** = работает сейчас
- **inactive + дата >30 дней** = вероятно мёртв
- **inactive + n/a** = никогда не запускался
- **not-found** = unit file удалён, запись висит
- **inactive service + active timer** = НЕ МЁРТВ, запускается по таймеру!

### Шаг 1.5: Проверить выходные файлы сервиса (новое — 12.07.2026)
Самый надёжный способ отличить живую рутину от мёртвой — проверить её выходные файлы:

```bash
# Дата модификации выходного файла
ls -la /path/to/service/output.log  # если обновлён сегодня/недавно — сервис реально работает

# Или проверить логи
tail -5 /var/log/service-log.log
```

**Реальный кейс (12.07.2026):** 
- `rclone_bisync.log` — 132K, обновлён 5 мин назад → **СЕРВИС ЖИВ**, синхронизирует OneDbContext каждые 5 минут
- `SELF_AWARENESS.md` — обновлён сегодня, но анализирует мёртвый `grigoriy-router.service` → мёртвый код, жив только таймер
- `unified_memory.db` — последняя запись 2 июня, хотя консолидатор запускается ежедневно в 04:00 → мёртв, ничего не делает

### Шаг 2: Проверить ExecStart и файл на диске
```bash
# Что запускает
systemctl cat <service> | grep -E "ExecStart|Description"

# Есть ли файл
ls -la /path/from/ExecStart
```

- Если файла нет — сервис гарантированно мёртв
- Если файл есть — может быть sandbox/эксперимент или legacy

### Шаг 3: Проверить, ссылается ли кто-то на сервис в живой инфраструктуре
Проверять ТОЛЬКО production-файлы:
```bash
# Caddy
grep -n "имя_сервиса\|путь_к_файлу" /etc/caddy/Caddyfile

# Cron
crontab -l | grep "имя_сервиса\|путь_к_файлу"

# Hermes config
grep "имя_сервиса" /root/.hermes/config.yaml

# Текущие Python-скрипты (не sandbox/, не backups/)
grep -r "имя_сервиса" /opt/zinaida/meta_agent/*.py 2>/dev/null
grep -r "имя_сервиса" /opt/zinaida/scripts/*.py 2>/dev/null
```

НЕ проверять (мусор): sandbox/, backups/, .git/

### Шаг 4: Категоризация
| Категория | Критерий | Что делать |
|-----------|----------|-----------|
| **МУСОР** | Не запускался >30 дней, файл есть/нет, никто не ссылается | Удалить |
| **ЗАМЕНЁН** | Функция переехала на другой сервис/компонент | Удалить, указать чем заменён |
| **НЕДОДЕЛКА** | Никогда не запускался, скрипт в sandbox/эксперимент | Удалить |
| **УСЛОВНО НУЖЕН** | Есть valid use-case, но не running (sync/backup) | Оставить или разобраться |
| **БЕЗ ФАЙЛА** | ExecStart ведёт в никуда | Удалить (гарантированно мёртв) |

### Шаг 5: Показать Олегу категоризированную таблицу
Формат:
```
### 🔴 МУСОР - N сервисов
| Сервис | Последний запуск | Почему умер |

### 🟡 Условно нужны - N сервисов
| Сервис | Причина оставить |

### 🟢 Активные - N сервисов
(только перечислить)
```

Дать вердикт и спросить решение. Не удалять без команды.

## Пример выполнения (Техник 8, 12.07.2026)

Из 26 zinaida-* сервисов:
- 7 active (роутеры, боты, core)
- 2 условно нужны (sync, backup)
- 1 not-found (уже удалён)
- **16 мусор** — не запускались 37-47 дней, заменены на Mem0/voice_assistant/новые роутеры, 2 файла отсутствуют на диске, никто не ссылается

## Питфоллы
- **Не путать systemctl is-enabled с is-active.** Сервис может быть disabled и не запускаться, но нужен для триггера (timer).
- **service с ExecStart=/bin/sleep infinity** — пустышка для legacy-совместимости. Не удалять пока не убедишься что никто на него не подписан (Wants/Requires/BindsTo).
- **Дата последней активации** — не гарантия что сервис не нужен. Некоторые сервисы (weekly-backup) запускаются раз в неделю по таймеру. Проверять timer.
- **static vs enabled vs disabled** — static = не поддерживает enable/disable (OneShot, обычно). Не признак мёртвости.
- **В sandbox/backups/ могут быть упоминания мёртвых сервисов** — это нормально, архивы не трогать.
