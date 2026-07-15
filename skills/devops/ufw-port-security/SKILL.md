---
name: ufw-port-security
description: "Настройка UFW для защиты сервера. Закрытие лишних портов, аудит открытых портов, идентификация процессов, правила для production. Использовать при задачах по безопасности, портам, firewall."
version: 1.0.0
author: Zinaida
license: MIT
metadata:
  hermes:
    tags: [ufw, firewall, ports, security, audit, production]
    related_skills: [zinaida-tech-protocol, production-change-protocol]
---

# UFW Port Security — Протокол настройки

## Аудит открытых портов

```bash
# Все порты, слушающие снаружи (0.0.0.0:PORT)
ss -tlnp | grep "0.0.0.0:"

# Идентификация — что за процесс на порту
ss -tlnp | grep "0.0.0.0:" | while read line; do
  port=$(echo "$line" | awk '{print $4}' | cut -d: -f2)
  pid=$(echo "$line" | grep -oP 'pid=\K[0-9]+')
  if [ -n "$pid" ]; then
    cmd=$(ps -p "$pid" -o args= 2>/dev/null | head -c 120)
    echo "Порт $port → $cmd"
  fi
done
```

## Стандартные открытые порты сервера (должны быть открыты)

| Порт | Сервис | Нужен снаружи? |
|------|--------|----------------|
| 22/2222 | SSH | ✅ Да |
| 80 | Caddy HTTP | ✅ Да |
| 443 | Caddy HTTPS | ✅ Да |
| 5000 | VK bot webhook | ✅ Да (получает VK Callback) |

## Порты, которые ДОЛЖНЫ быть закрыты (только localhost)

| Порт | Сервис | Опасность |
|------|--------|-----------|
| 2019 | Caddy admin API | Управление веб-сервером |
| 8002, 8003, 8005 | LLM роутеры | Прямой доступ к моделям |
| 8642 | Hermes Gateway | API управления |
| 8648 | Hermes Studio Web UI | Интерфейс управления |
| 9090, 9091 | HTTP-шары | Доступ к /root |
| 10200 | TTS сервер | Голосовой синтез |
| 6379 | Redis | База данных |
| 6333 | Qdrant | Vector DB |
| 8900, 8901 | Прокси | LLM fallback |

## HTTP-шары — особая опасность

```bash
# Найти HTTP-шары (python3 -m http.server)
ps aux | grep "http.server" | grep -v grep
# Убить:
kill <PID>
# Проверить:
ss -tlnp | grep -E "9090|9091"
```

**Типичный вид HTTP-шары:** `python3 -m http.server 9090 --bind 0.0.0.0`

**Опасность:** ОТКРЫВАЕТ ВЕСЬ /root или папку загрузок наружу. Любой может скачать файлы.

## Настройка UFW (включение)

```bash
# 1. Бэкап текущих правил
iptables-save > /opt/zinaida/backup_iptables_YYYYMMDD.txt

# 2. Сброс (если нужно)
ufw --force disable
ufw --force reset

# 3. Базовые политики
ufw default deny incoming
ufw default allow outgoing

# 4. Разрешить нужное
ufw allow 2222/tcp comment "SSH"
ufw allow 80/tcp comment "Caddy HTTP"
ufw allow 443/tcp comment "Caddy HTTPS"
ufw allow 5000/tcp comment "VK bot webhook"

# 5. Включить
ufw --force enable
ufw status verbose
```

## Проверка после включения

```bash
# Снаружи порты
ss -tlnp | grep "0.0.0.0:" | grep -vE ":2222|:80|:443|:5000"
# → должно быть пусто (кроме разрешённых)

# UFW статус
ufw status numbered

# Проверка что нужные сервисы работают
curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/  # → 200
systemctl is-active hermes-gateway  # → active
