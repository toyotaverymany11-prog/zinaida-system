# Упаковка системы Zinaida для передачи сотруднику

**Дата исследования:** 2026-07-10
**Полный отчёт:** `/opt/zinaida/onboarding_agent_research.md` (1025 строк)
**Исследованные проекты:** Hermes Agent, Open WebUI, OpenClaw, Coolify, Supabase, n8n

---

## Три подхода — от простого к замкнутому

### 🥇 GitHub Template + bootstrap-скрипт (рекомендован)
Репозиторий с `install.sh` + `docker-compose.yml` + `.env.example`.

```bash
curl -fsSL https://github.com/zinaida/zinaida-factory/install.sh | bash
```

**Скрипт (паттерн Coolify/Supabase):**
1. `check_root()` — проверка root/sudo
2. `detect_os()` — определение ОС (debian/rhel/arch/alpine/sles)
3. `check_deps()` — проверка curl, wget, git, jq, openssl через `command -v`
4. `install_docker()` — установка Docker через `curl -fsSL https://get.docker.com | sh`
5. `gen_secrets()` — генерация паролей через `openssl rand -hex 16`
6. `deploy()` — `docker compose pull && docker compose up -d`
7. `show_success()` — вывод URL и API-ключей

**Флаги:** `-y` (non-interactive), `--dry-run`, `--version`, `--help`

### 🥈 Docker Compose (контейнеризация)
Каждый компонент в отдельный контейнер:

| Сервис | Образ | Порт |
|--------|-------|------|
| zinaida-router | кастомный (openai-прокси) | 8002 |
| zina2-router | кастомный (DeepSeek роутер) | 8003 |
| vision-proxy | кастомный | 8901 |
| telegram-bot | кастомный | - |
| qdrant | qdrant/qdrant | 6333 |
| hermes-gateway | nousresearch/hermes-agent | (host) |
| hermes-dashboard | nousresearch/hermes-agent | 8648 |
| caddy | caddy:alpine | 443 |

**Сеть:** bridge (для изоляции) или host (проще, как в Hermes Agent)
**Volumes:** named volumes для БД, bind-mounts для конфигов
**Env:** единый `.env` с `VAR=${VAR:-default}`

### 🥉 Агент-установщик (onboarding skill)
После установки загружается SKILL.md, который:
1. Проверяет 7 сервисов (Qdrant 6333, роутеры, Telegram, Caddy)
2. Спрашивает API-ключи пользователя (Mistral, GitHub Models, DeepSeek)
3. Сохраняет в `.env` через `hermes config set`
4. Знакомит с контент-фабрикой

---

## Архитектура bootstrap-скрипта (рекомендованная)

```bash
#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
LOG_FILE="/tmp/zinaida-install-$(date +%Y%m%d-%H%M%S).log"

# Цветной вывод
info()  { echo -e "\\033[0;32m[INFO]\\033[0m $*" | tee -a "$LOG_FILE"; }
error() { echo -e "\\033[0;31m[ERROR]\\033[0m $*" >&2; }

# trap cleanup
cleanup() { rm -rf "$TEMP_DIR" 2>/dev/null || true; }
trap cleanup EXIT

# Функции:
check_root()    { [ "$(id -u)" -eq 0 ] || die "Root required"; }
detect_os()     { . /etc/os-release; case "$ID" in ... esac; }
check_deps()    { for dep in curl docker; do command -v "$dep" || install_$dep; done; }
check_disk()    { local free=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//'); [ "$free" -lt 10 ] && die "<10GB free"; }
gen_env()       { openssl rand -hex 16 > /dev/null; }
deploy()        { docker compose pull && docker compose up -d; }

main() { check_root; detect_os; check_deps; check_disk; gen_env; deploy; print_success; }
main "$@"
```

---

## Бесплатные модели для онбординга нового сотрудника

| Модель | RAM | Контекст | Как подключить |
|--------|-----|----------|----------------|
| **Ollama + Qwen3-8B** | ~5GB | 128K | `curl -fsSL https://ollama.com/install.sh | sh` → `ollama pull qwen3` → `hermes config set model ollama` |
| **Nous Portal** (облако) | 0 | 300+ моделей | `hermes setup --portal` (OAuth) |
| **DeepSeek Flash Free** | 0 | 128K | Бесплатный API через роутер. Ключ в `config/secrets.env` |
| **GitHub Models** | 0 | gpt-4o-mini | Бесплатный tier, ~10s, vision умеет |

---

## Ключевые референсы

- **Coolify install.sh** (1056 строк, эталон): https://github.com/coollabsio/coolify/blob/main/scripts/install.sh
- **Supabase setup.sh**: https://github.com/supabase/supabase (sparse-clone репозитория)
- **Hermes Agent Docker compose**: https://github.com/NousResearch/hermes-agent/blob/main/docker-compose.yml
- **Open WebUI compose**: https://github.com/open-webui/open-webui/blob/main/docker-compose.yaml
- **OpenClaw compose**: https://github.com/openclaw/openclaw/blob/main/docker-compose.yml

---

## ⚠️ КРИТИЧЕСКОЕ РАЗЛИЧИЕ: ИНФРАСТРУКТУРА vs ПРОДУКТ

При упаковке системы для передачи важно различать:

| Сущность | Что это | Где живёт |
|----------|---------|-----------|
| **Инфраструктура (платформа)** | Hermes Agent + роутеры + память + скрипты. То, на чём работает агент. | На сервере: `/opt/zinaida/`, `~/.hermes/`. Описана в `SYSTEM_SNAPSHOT.md`. |
| **Продукт (персонаж)** | Telegram-бот Зинаида с токенами, тестами, quality gates, safety router, Relationship Lab. Сам персонаж. | В отдельном репозитории (системная карта: `zinaida_system_map.html`). |

**SYSTEM_SNAPSHOT.md** на сервере описывает ТОЛЬКО инфраструктуру. Не путать с системной картой продукта (HTML-файл с ланами, чек-листами, идеями).

При передаче сотруднику:
- Инфраструктура = он получает сервер / Docker / доступ
- Продукт = он получает код репозитория с Telegram-ботом
- Между ними — Hermes API (мост)

## Точный список исключения контент-завода

Когда Олег говорит «без контент-завода», ИСКЛЮЧИТЬ:

| Категория | Конкретно |
|-----------|-----------|
| **Базы данных** | `phases.db`, `smm_rag.db`, `content_rotation.db`, `analytics.db`, `design_assets.db` |
| **Папки проекта** | `inbox/PROJECTS/Otnoshenya/`, `SmmFabrika/` |
| **Скрипты** | `content_factory.py`, `curator_job.py`, `fix_design_feedback.py`, `register_design.py`, `record_feedback.py` |
| **Дизайн** | `zinaida_passport/`, `shared_memory/design_feedback.md` |
| **Навыки SMM** | `smm_channel_planner.md`, `smm_hashtag_master.md`, `smm_image_prompter.md`, `smm_queue_planner.md`, `smm_researcher.md`, `smm_strategist.md`, `smm_strategy_planner.md` |
| **Навыки copywriting** | `copywriting/zinaida-content-factory`, `copywriting/zinaida-operations`, `copywriting/brand-font-zinaida` |

**ВКЛЮЧИТЬ обязательно:** конфиги Hermes и роутеров, навыки devops/mlops/consilium, скрипты инфраструктуры, Telegram-бот, Mem0, persona (SOUL.md, AGENTS.md).

## Практический результат (10.07.2026)

Создан пакет `/tmp/zinaida-infra/`, запушен в `toyotaverymany11-prog/Zinaida-vk-app/infra/` (commit есть, пуш не прошёл — GITHUB_TOKEN без git-прав):
- **124 файла**, **1.4 MB**
- `install.sh` + `docker-compose.yml` + `.env.example` + `README.md`
- 92 навыка (только infra: devops, mlops, consilium-collect, persona)
- 11 файлов роутеров (zinaida_openai_proxy, zina2_router и др.)
- 8 скриптов (tech_diagnostic, deep_research, consilium)
- Telegram bot (bot.py, notify.py)
- Mem0 MCP сервер
- Onboarding-скилл (FedorOnboarding.md) — автоматический гид при первом входе
- Persona (SOUL.md, AGENTS.md)
- Документация (README, onboarding.md)

**Критические уроки этого кейса:**

### GitHub Push Protection (Secret Scanning)
При пуше GitHub блокирует коммиты с реальными API-ключами даже в дефолтных значениях `os.environ.get("KEY", "реальный_ключ")`.
**Фикс:** перед коммитом заменить ВСЕ реальные ключи/токены на `"xxx"`:
```bash
grep -rn 'ghp_\|sk-or-\|r8_' infra/ --include='*.py' --include='*.md' | grep -v 'xxx' | grep -v '\.\.\.'
```
Если блокировка уже произошла: `git commit --amend` (исправить ключи) → `git push --force-with-lease`

### Personal Access Token для git push
GitHub Models API токен (`ghp_` с правами models) НЕ РАБОТАЕТ для git push. Нужен отдельный токен.
**Создание:** GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
**Нужна одна галочка:** `repo` (Full control of private repositories) — всё остальное лишнее.
**Использование:** `git remote set-url origin https://USERNAME:TOKEN@github.com/USER/REPO.git`

### Делаем репозиторий приватным + добавляем collaborator
1. Открыть https://github.com/USER/REPO/settings
2. Слева General → листать вниз до Danger Zone → Change visibility → Private
3. Слева Access → Collaborators → Add people → ввести username → роль Write

### Структура инструкции новому разработчику (для отправки одним сообщением)
```
Ссылка: https://github.com/USER/REPO

Шаги:
1. git clone https://github.com/USER/REPO.git
2. cd REPO/infra
3. cp .env.example .env
4. nano .env     # вставь свои ключи (Mistral/DeepSeek/GitHub)
5. ./install.sh

После установки → http://localhost:8648 → напиши "техник"
Инструкция: docs/onboarding.md
```

### Как давать инструкции в GitHub (для Олега на iPad)
- GitHub на iPad показывает страницу иначе чем на десктопе
- Settings репозитория: прямой URL https://github.com/USER/REPO/settings
- Danger Zone (Опасная зона) — красная секция в самом низу General
- Collaborators — слева в колонке, пункт Access или Collaborators

**Критические уроки этого кейса (в более широком смысле):**
- `delegate_task` для исследований = создание мусорных сессий в Web UI через `hermes_studio_use_chat_run`. ЗАПРЕЩЕНО. Всё в одном чате.
- GITHUB_TOKEN (для GitHub Models API) НЕ РАБОТАЕТ для git push. Нужен отдельный Personal Access Token с repo scope или SSH-ключ.
- Оценки в днях («2-3 дня») → ярость. Реальность: 40 минут на весь пакет.
- Контент-завод НЕ ВХОДИТ в пакет для сотрудника. Список исключения — в этом документе выше.
- Между «инфраструктурой» и «продуктом» — Hermes API. Фёдор разрабатывает персонажа (продукт), используя инфраструктуру (платформу).

## WOW-идеи
- `--cloud` флаг: разворачивает систему на VPS через SSH (парень даёт IP + ключ)
- GitHub Codespaces / GitPod бейдж — запуск без локальной установки
- После установки автоматически запускать onboarding-скилл с гидом
