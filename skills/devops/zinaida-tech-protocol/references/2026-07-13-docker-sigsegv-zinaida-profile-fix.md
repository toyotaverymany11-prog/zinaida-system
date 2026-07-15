# Техник 13 — Docker SIGSEGV recovery и Zinaida profile fix
## Дата: 13.07.2026

---

## 1. Docker SIGSEGV после чистки JSON файлов

**Симптом:**
```
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation]
daemon.(*Daemon).register() container.go:92
```
Docker не стартует после чистки `/var/lib/docker/*.json` от упоминаний n8n.

**Причина:** битый `config.v2.json` контейнера. При чистке JSON были удалены поля `Name` или `ID` в конфиге какого-то контейнера.

**Диагностика:**
```bash
dockerd 2>&1 | grep "register\|container.go\|config.v2"
# Если падает на register() — проблема в config.v2.json контейнера
```

**Фикс:**
```bash
# 1. Найти битый контейнер
for dir in /var/lib/docker/containers/*/; do
  python3 -c "
import json
try:
    with open('$dir/config.v2.json') as f:
        d = json.load(f)
    name = d.get('Name', '')
    if not name:
        print(f'БИТЫЙ: $dir')
except Exception as e:
    print(f'ОШИБКА: $dir -> {e}')
"
done

# 2. Удалить битую папку
rm -rf /var/lib/docker/containers/<broken_id>/

# 3. Запустить Docker
systemctl start docker.service
```

**Профилактика:** никогда не чистить /var/lib/docker/*.json вручную скриптами. Использовать `docker` CLI для всех операций.

---

## 2. Zinaida profile model.default fix

**Симптом:** агент в профиле `zinaida` (Character Architect) не отвечает, получает пустой стрим.

**Причина:** `model.default: Zinaida-Router` в `/root/.hermes/profiles/zinaida/config.yaml`. 8002 роутер не умеет стримить с именем модели `Zinaida-Router` — он ищет провайдера по этому имени, не находит, возвращает пустой стрим.

**Фикс:**
```bash
# В /root/.hermes/profiles/zinaida/config.yaml:
# Было:
model:
  default: Zinaida-Router
# Стало:
model:
  default: deepseek-chat
```

После изменения — перезапустить Gateway:
```bash
systemctl restart hermes-gateway
```

**Проверка:** создать новую сессию в Hermes Studio с профилем zinaida — агент должен отвечать нормально.
---

## 3. Связанные навыки
- `devops/zinaida-n8n-kill` — полный протокол убийства контейнера
- `devops/zinaida-tech-protocol` — общий технический протокол
