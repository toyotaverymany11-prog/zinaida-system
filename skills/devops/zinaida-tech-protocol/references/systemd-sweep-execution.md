# Systemd Sweep Execution Protocol

После того как аудит (см. systemd-dead-service-audit.md) выявил мёртвые сервисы, и Олег сказал «чисти» — протокол удаления.

## Жёсткие правила
- **Ничего не удалять без бэкапа**. Все .service и .timer файлы — в одну папку.
- **Проверять таймеры** перед сервисами. Timer может делать inactive service нужным.
- **daemon-reload** только после удаления ВСЕХ файлов.
- **Финальная проверка** всех active сервисов — роутеры, боты, Caddy.

## Порядок выполнения

### Шаг 0: Бэкап ВСЕХ unit-файлов
```bash
mkdir -p /opt/zinaida/backups/systemd-$(date +%Y%m%d)
cp -v /etc/systemd/system/zinaida-*.service /etc/systemd/system/zina2-*.service \
      /etc/systemd/system/vkbot.service /etc/systemd/system/obushenie-mounts.service \
      /etc/systemd/system/zinaida-*.timer \
      /opt/zinaida/backups/systemd-$(date +%Y%m%d)/ 2>&1
```

### Шаг 1: Удалить мёртвые таймеры (сначала timer, потом service)
Таймеры надо удалять ДО сервисов, иначе systemd может породить ошибки зависимостей.

```bash
# Золотой шаблон для одного юнита:
systemctl stop имя.timer 2>/dev/null
systemctl disable имя.timer 2>/dev/null
rm -f /etc/systemd/system/имя.timer

systemctl stop имя.service 2>/dev/null
systemctl disable имя.service 2>/dev/null
rm -f /etc/systemd/system/имя.service
```

Вариант для групп (если сервисов много):
```bash
# Фаза 1: таймеры
for unit in имя1 имя2 имя3; do
  systemctl stop zinaida-${unit}.timer 2>/dev/null
  systemctl disable zinaida-${unit}.timer 2>/dev/null
  rm -f /etc/systemd/system/zinaida-${unit}.timer
done

# Фаза 2: сервисы
for unit in имя1 имя2 имя3; do
  systemctl stop zinaida-${unit}.service 2>/dev/null
  systemctl disable zinaida-${unit}.service 2>/dev/null
  rm -f /etc/systemd/system/zinaida-${unit}.service
done
```

### Шаг 2: Массовое удаление (когда список большой)
```bash
for unit in \
  admin api chat-api dashboard gateway memory runtime toolgateway upload \
  tts bot autonomous-heartbeat autopilot engine healer provider-audit \
  provider-auditor public-api sorter system-monitor vk vk-public vkbot \
  chat-bridge command-bridge live-status promoter self-diagnostic sysaudit; do

  srv="zinaida-${unit}.service"
  f="/etc/systemd/system/${srv}"
  if [ -f "$f" ]; then
    systemctl stop "$srv" 2>/dev/null
    systemctl disable "$srv" 2>/dev/null
    rm -f "$f"
    echo "✅ ${srv} — удалён"
  else
    echo "- ${srv} — файла нет"
  fi
done
```

### Шаг 3: daemon-reload
```bash
systemctl daemon-reload
```

### Шаг 4: Финальная проверка
```bash
# 4.1. Какие zinaida- сервисы остались (должны быть только активные)
systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -E "zina|vkbot|obushenie" | sort

# 4.2. Проверить что все активные живы
for srv in zina2-router zina2-router-8005 zinaida-router zinaida-telegram-bot \
           zinaida-core vkbot obushenie-mounts; do
  act=$(systemctl is-active $srv 2>&1)
  printf "%-35s %s\n" "$srv" "$act"
done

# 4.3. Проверить здоровье роутеров
curl -s -o /dev/null -w "8002: HTTP %{http_code}\n" http://127.0.0.1:8002/health
curl -s -o /dev/null -w "8003: HTTP %{http_code}\n" http://127.0.0.1:8003/health
curl -s -o /dev/null -w "8005: HTTP %{http_code}\n" http://127.0.0.1:8005/health

# 4.4. Telegram и VK
systemctl is-active zinaida-telegram-bot
systemctl is-active vkbot

# 4.5. Docker контейнеры живы?
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Шаг 5: Проверить что таймеров-зомби не осталось
```bash
systemctl list-units --type=timer --all --no-legend | grep zinaida
# Должен остаться только zinaida-weekly-backup.timer
```

## Питфоллы

- **Не путать stop и disable.** stop выключает сейчас, disable убирает из автозагрузки. Делать ОБА.
- **Файл на диске vs systemctl.** Если `systemctl cat` показывает файл, а `ls` не находит — удалено другим процессом. Просто запустить daemon-reload.
- **static vs enabled.** Сервисы с enabled=static не имеют enable/disable. Их можно только stop + rm.
- **not-found.** Если systemctl показывает `not-found`, unit-файла уже нет — просто daemon-reload.
- **Бэкап в `/opt/zinaida/backups/`.** Не в /tmp и не в /root/ — туда Олег не смотрит.

## Реальный кейс (Техник 8, 12.07.2026)

Удалили 33 .service + 14 .timer файлов за один сеанс.
- Бэкап: /opt/zinaida/backups/systemd-20260712/ (61 файл)
- Потери: 0 сбоев. Все роутеры и боты живы.
- Итого: было 42 systemd-юнита → стало 8 (7 active + 1 backup timer)
