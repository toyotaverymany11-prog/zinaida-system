---
name: production-change-protocol
description: How to safely modify running production services (routers, systemd services, Hermes config) on the Zinaida content factory stack. Backup → side-by-side → test → integrate workflow. Prevents "сломал production без бэкапа" incidents.
triggers:
  - modify the router
  - change the router
  - fix the router
  - update the service
  - production change
  - поменять роутер
  - исправить роутер
  - обновить сервис
  - production изменение
  - не сломать production
  - починить не сломав
related_skills:
  - hermes-studio-integration
  - hermes-agent
---

# Production Change Protocol

## When to use
Любое изменение **работающего production-сервиса**. Неважно — роутер, systemd-сервис, конфиг Hermes, или скрипт генерации контента. Если сервис сейчас обрабатывает запросы реальных пользователей — этот протокол обязателен.

## Card — Research → Copy → Apply → Run → Deploy

### 0. Исследуй ПРЕЖДЕ чем строить (новая система)
Если Олег просит установить или внедрить новую систему — НЕ начинай с установки.
Сначала проведи глубокое исследование:

**Протокол «изучи перед установкой»:**
1. **Документация** — прочитай официальные docs, найди quickstart и production-рекомендации
2. **GitHub issues** — поищи common mistakes, проблемы новичков, breaking changes
3. **Reddit** — r/mcp, r/LocalLLaMA, r/ClaudeAI — что люди реально пишут про опыт использования
4. **Блоги и сравнения** — vectorize.io, medium — объективные сравнения
5. **Тикет #4573 (урок)**: 97.8% записей оказались мусором у пользователей Mem0. Это выяснилось только из GitHub issues. Если бы ставили без исследования — получили бы ту же проблему.
6. **Отчёт** — сохрани результаты в `references/` папку соответствующего навыка

**Критерий готовности к установке:** знаешь все типичные ошибки, правильный конфиг, production-паттерны.

### 1. Изучи ТЕКУЩЕЕ состояние
**Не доверяй git-истории — проверь что работает прямо сейчас.**

```bash
# Что сейчас запущено?
systemctl status zinaida-router --no-pager -l

# Что отвечает?
curl -s -w "\nHTTP:%{http_code}" http://127.0.0.1:8002/status

# Какой файл реально используется?
ls -la /opt/zinaida/meta_agent/

# Есть ли отличия от git?
cd /opt/zinaida && git diff HEAD -- meta_agent/zinaida_openai_proxy.py
```

**Типовая ошибка:** git-коммит показывает v2.0 (без DeepSeek), но на сервере запущена v4.0 (с DeepSeek). Сравнивай файл на диске, не только коммит.

### 2. Создай бэкап

```bash
cp /opt/zinaida/meta_agent/target.py /opt/zinaida/meta_agent/target.py.BACKUP_$(date +%Y%m%d_%H%M%S)
cp /opt/zinaida/meta_agent/target.py /opt/zinaida/meta_agent/target.py.BACKUP_CURRENT
```

**Два бэкапа:** один с таймштампом (для истории), второй `BACKUP_CURRENT` (чтобы быстро откатиться, не вспоминая имя файла).

### 3. Работай в сторонке
**Не редактируй production-файл.** Создай рядом новый файл:

```
/opt/zinaida/meta_agent/
├── zinaida_openai_proxy.py       # ← НЕ ТРОГАТЬ (production)
├── zinaida_openai_proxy.py.NEW   # ← РАБОТАТЬ ЗДЕСЬ (новая версия)
└── zinaida_openai_proxy.py.BACKUP_20260708_091620  # ← бэкап
```

Для нового сервиса — отдельный файл с другим именем (например `zina2_router.py` для порта 8003).

### 4. Тестируй изолированно
**Запусти на отдельном порту, проверь что отвечает корректно.**

```bash
# Ручной запуск на тестовом порту
python3 /opt/zinaida/meta_agent/new_file.py &
sleep 2

# Проверка health
curl -s http://127.0.0.1:<test_port>/health

# Тест реального запроса (короткий)
curl -s -X POST http://127.0.0.1:<test_port>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

**Критерии готовности к интеграции:**
- Health endpoint отвечает 200
- Реальный LLM-запрос проходит (не graceful fallback)
- Статус endpoint показывает корректные данные

### 5. Только потом — интегрируй

```bash
# Останови старый сервис (если меняется порт)
systemctl stop old-service

# Скопируй новый файл на место (если нужно)
cp new_file.py production_file.py

# Создай systemd-сервис (если новый)
cat > /etc/systemd/system/new-service.service << 'EOF'
[Unit]
...
EOF
systemctl daemon-reload
systemctl enable new-service
systemctl start new-service

# Проверь
systemctl status new-service --no-pager
curl -s http://127.0.0.1:<port>/health
```

### 6. Обнови конфиги
Если добавляешь новый провайдер в Hermes — добавь его в `/root/.hermes/config.yaml`:

```yaml
  zina2-router:
    api: http://127.0.0.1:8003/v1
    api_key: dummy-key
    default_model: Zina2-Router
    name: zina2-router
```

### 7. GitHub secret sanitisation (перед push)
Перед push в GitHub — ПРОВЕРИТЬ что в коде нет реальных API-ключей/токенов. GitHub Push Protection блокирует коммиты с секретами.

```bash
# Сканировать на типовые секреты
grep -rn 'ghp_\|sk-or-\|r8_\|73c9e5' . --include='*.py' --include='*.md' --include='*.yaml' 2>/dev/null | grep -v 'xxx' | grep -v '\.\.\.' | grep -v 'example'
```

Если найдено — заменить на `"xxx"` и `git commit --amend` (force push).

**PAT для git push — критическое различие типов токенов GitHub:**
- **GitHub Models API токен** (`ghp_` с правами models) — НЕ РАБОТАЕТ для git push. Выдаёт "Invalid username or token".
- **Personal Access Token (classic)** — нужен отдельный, с единственной галочкой `repo`.
- **Fine-grained token** — тоже подходит, нужны права `contents: write` + `metadata: read`.
- **Механизм блокировки:** GitHub Push Protection сканирует коммиты на лету. Если токен или другой секрет обнаружен в diff — пуш блокируется даже если у токена есть права. Фикс: заменить секрет на `"xxx"` в коде, `git commit --amend`, `git push --force-with-lease`.

**Создание PAT для git:**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Поставить ТОЛЬКО `repo` (Full control of private repositories)
4. Сгенерировать, скопировать, использовать: `git remote set-url origin https://USERNAME:TOKEN@github.com/USER/REPO.git`

**Проверка токена перед пушем:**
```bash
curl -s -H "Authorization: token ghp_xxx" https://api.github.com/repos/USER/REPO
# Если permissions.push === true — токен работает
```

### 8. Сообщи оператору
"Готово. Новый сервис на порту N работает, старый не троган."

## Pitfalls

### ❌ Редактирование production-файла напрямую
Даже «мелкая правка» может сломать.

### 🚨 КРИТИЧЕСКИЙ ЗАПРЕТ: Не редактировать config.yaml через sed/python/cat
`config.yaml` — **НЕЛЬЗЯ** править через sed, echo, python, cat с heredoc. Только:
- `hermes config set <key> <value>` — для отдельных настроек
- MCP API (`hermes_studio_use_provider_add/delete`) — для провайдеров
- `hermes config edit` — открыть в редакторе

**Симптом ошибки:** после sed/редактирования конфиг повреждается, Hermes Studio перестаёт загружать модели, поле контекста сбрасывается на дефолт (256 вместо 800K), все провайдеры исчезают из панели.

**Восстановление:** `cp /root/.hermes/config.yaml.bak /root/.hermes/config.yaml` (бэкап создаётся автоматически перед изменениями).

### ❌ Изменение только в одном роутере
Даже если фича кажется применимой только к одному роутеру — всегда проверь, можно ли её применить к остальным. Oleg's rule (13.07.2026): "Все во все роутеры надо встраивать абсолютно".
Список роутеров: 8002 (zinaida_openai_proxy.py), 8003 (zina2_router.py), 8005 (router_8005_v2.py).
Перезапуск systemd-сервиса сразу после правки — гарантированный способ получить простой.

### ❌ Сравнение с git вместо текущего файла
git может показывать версию до последних hotfix-правок. Всегда проверяй `systemctl status` и `curl` текущего инстанса.

### ❌ os.environ.setdefault() не перезаписывает systemd-ключи (11.07.2026)
Если systemd-сервис устанавливает `Environment="DEEPSEEK_API_KEY=***"`, то `os.environ.setdefault()` не перезапишет его значением из .env. Роутер будет использовать **мёртвый systemd-ключ**, думая что работает с живым.

**Симптом:** health endpoint показывает другой префикс ключа, чем в .env файле.

**Правило:** Ключи для LLM-провайдеров читать напрямую из .env через `open().read()`, а не через `os.getenv()`:
```python
# ❌ os.getenv() может вернуть systemd-значение
key = os.getenv("DEEPSEEK_API_KEY", "")

# ✅ Читать напрямую из файла
with open("/opt/zinaida/.env", "r") as f:
    for line in f:
        if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
            key = line.split("=", 1)[1].strip()
            break
```

### ❌ Доверять комментарию о порте в хедере файла (11.07.2026)
Файл `router_8005_v2.py` в docstring пишет «Порт: 8004 (тестовый)», но `uvicorn.run()` на строке 848 использует `port=8005`. Всегда проверять точную строку `uvicorn.run()` или аргументы systemd сервиса, а не docstring.

### ❌ Docker JSON corruption from clean-sweeping (13.07.2026 — Техник 13)

Подробный кейс восстановления: `references/docker-json-corruption-recovery.md`

### ❌ Изменение /v1/models без проверки в Hermes Studio (13.07.2026)

При изменении списка моделей в роутере (эндпоинт `/v1/models`):
1. Править ТОЛЬКО эндпоинт, не трогать логику классификации.
2. После рестарта: `curl -s http://127.0.0.1:PORT/v1/models` — проверить ответ.
3. Переключиться на профиль в Hermes Studio — проверить что отображение изменилось.
4. Убедиться что модель по умолчанию в custom_providers всё ещё существует в ответе роутера.
`find /var/lib/docker -type f -name "*.json" -exec ...` модификация JSON файлов внутри `/var/lib/docker` может сломать Docker daemon полностью.

**Симптом:** Docker падает с segfault при старте:
```
panic: runtime error: invalid memory address or nil pointer dereference
github.com/moby/moby/v2/daemon.(*Daemon).register(0x...).container.go:92
```

**Причина:** Docker daemon ожидает определённую структуру в config.v2.json каждого контейнера. Если удалить поля (Name, Image), daemon получает nil pointer при restore. Редактирование repositories.json или manifest файлов может оставить их битыми.

**Фикс при segfault от битого контейнера:**
```bash
# 1. Найти битый контейнер (без имени)
for dir in /var/lib/docker/containers/*/; do
  python3 -c "
import json
with open('$dir/config.v2.json') as f:
    d = json.load(f)
if not d.get('Name', ''):
    print(f'БИТЫЙ: $dir')
" 2>/dev/null
done

# 2. Удалить битую папку контейнера
rm -rf /var/lib/docker/containers/БИТЫЙ_ХЕШ/

# 3. Если бит repositories.json — пересоздать
python3 -c "
import json
with open('/var/lib/docker/image/overlay2/repositories.json', 'w') as f:
    json.dump({'Repositories': {}}, f)
print('repositories.json восстановлен')
"

# 4. Запустить Docker
systemctl reset-failed docker.service
systemctl start docker.service
```

**Правило:** Не редактировать файлы внутри `/var/lib/docker/` вручную. Для удаления контейнера — `docker rm -f`. Для очистки образов — `docker image prune / docker rmi`. Только alpine-заглушка (`docker run alpine sleep infinity → docker commit → n8nio/n8n:latest`) — безопасна, работает через Docker API, не трогает файлы на диске.

### ❌ Редактирование config.yaml через execute_code с read_file
`read_file` по умолчанию отдаёт только 500 строк (лимит). Если обновить файл через `execute_code` после такого чтения — всё что после 500 строк просто исчезнет.
**Правильный способ для config.yaml:** использовать `patch` tool (find-and-replace, он сохранет весь файл) или `sed`/Python через `terminal()`. Никогда не читай config.yaml в execute_code и не записывай его целиком — только точечные правки.

### 🚨 ПРОВАЙДЕРЫ В PROFILE-SPECIFIC CONFIG.YAML — ОДИН BASE_URL = ОДИН ПРОВАЙДЕР (13.07.2026)

**Ситуация:** У каждого профиля (zinaida, agent2) есть свой `config.yaml` в `/root/.hermes/profiles/<profile>/`. В нём секция `custom_providers:` работает так же как в корневом конфиге.

**ЖЕЛЕЗНОЕ ПРАВИЛО:** Каждый уникальный `base_url` = ОДИН провайдер. Модели авто-обнаруживаются из API роутера (GET /v1/models).

**НЕ создавай N провайдеров для N моделей одного роутера.** Это создаёт в интерфейсе Hermes Studio N отдельных строк вместо одной с выпадающим списком моделей. Пользователь видит кашу и бесится.

**Как Hermes Studio отображает провайдеров:**
1. Читает `custom_providers` из config.yaml выбранного профиля
2. Группирует по `base_url` — один base_url = одна секция в UI
3. Вызывает GET `{base_url}/v1/models` — список моделей в этой секции
4. `model` поле в custom_providers = модель по умолчанию (выделена)

**Как проверить перед фиксацией:**
```bash
# Посчитать сколько провайдеров с одинаковым base_url
python3 -c "
import yaml
with open('/root/.hermes/profiles/zinaida/config.yaml') as f:
    cfg = yaml.safe_load(f)
urls = [p['base_url'] for p in cfg.get('custom_providers',[])]
from collections import Counter
for url, count in Counter(urls).items():
    if count > 1:
        print(f'❌ {url} — {count} провайдеров! Должен быть 1.')
    else:
        print(f'✅ {url} — 1 провайдер')
"
```

**Как контролировать, какие модели видны в Hermes Studio:**
Не через Hermes config — а через код роутера. Ответ `/v1/models` в роутере определяет, что увидит пользователь.

```python
# В файле роутера (например router_8005_v2.py):
@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "8005-Router", "object": "model", "owned_by": "local"},
            {"id": "8005-Enhanced", "object": "model", "owned_by": "local"},
            # Только те, что нужны пользователю. Остальные скрыты.
        ]
    }
```

**Правило именования провайдера:** `name` в custom_providers = то, что пользователь видит в UI. Коротко, понятно. Пример: `8005`, `zina2-router`, `zinaida-router`. Не надо называть `router-8005-flash` — пользователь не поймёт.

**Пример правильного конфига (3 провайдера, 1 на порт):**
```yaml
custom_providers:
  - base_url: http://127.0.0.1:8005/v1
    model: 8005-Enhanced
    name: 8005
  - base_url: http://127.0.0.1:8003/v1
    model: Zina2-Router
    name: zina2-router
  - base_url: http://127.0.0.1:8002/v1
    model: Zinaida-Router
    name: zinaida-router
```

### ✅ Безопасный способ: добавить модель к провайдеру через Hermes Studio API

Вместо правки config.yaml — использовать MCP API, чтобы добавить новую модель к существующему кастомному провайдеру:

```python
# Через hermes_studio_api_request (MCP):
# PUT /api/hermes/custom-model с body {"model": "НоваяМодель", "provider": "custom:имя-провайдера"}

# Это безопаснее правки config.yaml — не задевает YAML-структуру,
# не сбрасывает context_length, не ломает форматирование.
# Модель сразу появляется в Hermes Studio без перезапуска gateway.

# Чтобы модель была видна в роутере — добавить её ID в список /v1/models эндпоинта роутера.
```

**Ограничение:** этот метод только добавляет модель к уже существующему провайдеру. Для нового провайдера используй `hermes_studio_use_provider_add`.

### 📸 Проверка: скриншот — это спецификация (13.07.2026)

Когда пользователь говорит «сделай как на скриншоте» — картинка является спецификацией. Не додумывай, не предполагай, не делай «как я считаю правильным».

**Протокол «скриншот = спецификация»:**
1. Посмотреть на скриншот через `vision_analyze` — выписать все элементы один-в-один
2. Сравнить с текущим состоянием — каждое расхождение = проблема
3. Исправить все расхождения
4. Показать пользователю и спросить «теперь совпадает?»

**Симптом ошибки:** пользователь скинул скриншот, а я сделал не как на скриншоте, а как я сам придумал.

## Renaming Hermes Profiles

1. `mv /root/.hermes/profiles/oldname /root/.hermes/profiles/newname`
2. Обновить SOUL.md, .hermes.md, config.yaml (если есть ссылки на имя)
3. Обновить shared_memory/AGENTS.md и корневую AGENTS.md
4. `printf "Y\nY\n" | hermes gateway install --profile newname` (через pty)
5. `hermes gateway start --profile newname`
6. `hermes profile list` — проверить running

## Automated Recurring Backups

For services that need **scheduled** rather than per-change backups, use the systemd timer + rsync hardlink pattern:

### Script
```bash
#!/bin/bash
BACKUP_BASE="/opt/zinaida.Backup"
SOURCE="/opt/zinaida"
DATE=$(date +%Y%m%d)
EXCLUDES=("--exclude=*.bak" "--exclude=*.tmp" "--exclude=node_modules/"
          "--exclude=__pycache__/" "--exclude=.git/" "--exclude=.npm/"
          "--exclude=sandbox/" "--exclude=backups/" "--exclude=archive/")
LAST_BACKUP=$(ls -1d ${BACKUP_BASE}.* 2>/dev/null | sort | tail -1 || echo "")
if [ -n "$LAST_BACKUP" ]; then
    rsync -a --delete --link-dest="$LAST_BACKUP" "${EXCLUDES[@]}" "$SOURCE/" "${BACKUP_BASE}.${DATE}/"
else
    rsync -a --delete "${EXCLUDES[@]}" "$SOURCE/" "${BACKUP_BASE}.${DATE}/"
fi
ls -1d ${BACKUP_BASE}.* | sort | head -n -4 | while read -r old; do rm -rf "$old"; done
```

Key: `--link-dest` makes unchanged files hardlinks — **zero extra space**. Keep 4 backups (1 month retention).

### Service + Timer
```ini
# /etc/systemd/system/zinaida-weekly-backup.service
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /opt/zinaida/scripts/weekly_backup.sh
Nice=19
IOSchedulingClass=idle
ExecStartPre=/usr/bin/bash -c 'if [ -f /tmp/backup.lock ]; then exit 75; fi; touch /tmp/backup.lock'
ExecStartPost=/usr/bin/rm -f /tmp/backup.lock

# /etc/systemd/system/zinaida-weekly-backup.timer
[Timer]
OnCalendar=Sun 04:00:00
Persistent=true
RandomizedDelaySec=30m
[Install]
WantedBy=timers.target
```

Activation: `systemctl daemon-reload && systemctl enable --now zinaida-weekly-backup.timer`

## Pipeline Latency Diagnosis

Use this when modifying a multi-stage service (router with pre/post-processing, verification, editing stages) and the user reports it's slow.

### Procedure
```bash
# 1. Check if service is actually running
ss -tlnp | grep <port>

# 2. Health check — validate keys/config loaded
curl -s http://127.0.0.1:<port>/health | python3 -m json.tool

# 3. Measure baseline — simple request
time curl -s -w "\nTIME_REAL=%{time_total}s" \
  -X POST http://127.0.0.1:<port>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"Привет"}],"stream":false}' 2>&1 | tail -1

# 4. Measure baseline — realistic (long) request
time curl -s -w "\nTIME_REAL=%{time_total}s" \
  -X POST http://127.0.0.1:<port>/v1/chat/completions \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"Напиши пост про..."}]}' 2>&1 | tail -1
```

### Stage-by-stage analysis
1. **Read the code** — enumerate every async function that makes an API call
2. **Estimate time per stage:**
   - Local function: <5ms
   - SQLite (local): <50ms
   - Mistral/Ollama API: 1-3s
   - DeepSeek Flash API: 2-4s
   - DeepSeek Pro API: 4-8s
   - GigaChat API (OAuth2): 3-4s + **mandatory 3s rate limit pause**
3. **Identify parallel vs sequential stages** — parallel stages don't add wall-clock time; sequential ones do
4. **Strip slowest stages first:**
   - GigaChat (3s pause) → disable if speed > editing quality
   - Mistral pre-processing (1-3s extra call) → disable, DeepSeek Flash handles it
   - Mistral verification (1-3s parallel) → disable if not paired with GigaChat editing
5. **Re-measure after each removal** — if time doesn't drop significantly, the bottleneck is elsewhere

### Compare with sibling services
```bash
# Same request on another router/proxy
time curl -s -w "\nTIME_REAL=%{time_total}s" \
  -X POST http://127.0.0.1:<sibling-port>/v1/chat/completions \
  -d '{"model":"<sibling-model>","messages":[{"role":"user","content":"тот же запрос"}]}' 2>&1 | tail -1
```
If the sibling (bare DeepSeek) is *slower* than the layered service, the pipeline is not the bottleneck — DeepSeek API itself is.

### Concrete example
See `references/8005-router-optimization-case.md` — full walkthrough of diagnosing Zina2 Router v2.0 (port 8005), stripping GigaChat+Mistral layers, comparing with 8003 sibling, and creating systemd service.

## Quick Reference

```bash
# Всё сделать одной серией:
# 1) Изучить
systemctl status zinaida-router --no-pager -l | head -15
curl -s http://127.0.0.1:8002/status | python3 -m json.tool

# 2) Забэкапить
cp file.py file.py.BACKUP_$(date +%Y%m%d_%H%M%S)

# 3) Создать новый файл
# (редактировать в сторонке)

# 4) Тест
python3 new_router.py &
sleep 2
curl -s http://127.0.0.1:<port>/status
curl -s -X POST ... -d '{"test":"data"}'
kill %1

# 5) Интеграция
systemctl link /etc/systemd/system/new.service
systemctl enable --now new.service
```
