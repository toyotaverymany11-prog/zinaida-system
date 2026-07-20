#!/usr/bin/env python3
"""
СИСТЕМА ПЕРЕНОС v2.0 | 2026-07-15
===================================
ПОЛНЫЙ сборщик системы Зинаиды — без упущений.
Всё что есть на сервере: инфра, навыки, триггеры, проекты, память, протоколы, дизайн.

Использование:
  python3 transfer_system_builder.py               # собрать отчёт
  python3 transfer_system_builder.py --output FILE  # сохранить в файл
"""

import os, sys, json, subprocess, hashlib
from datetime import datetime
from pathlib import Path

BASE = Path("/opt/zinaida")
OUT_DIR = BASE / "outbox" / "transfer_system"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKILLS_DIR = Path("/root/.hermes/skills")
HERMES_DIR = Path("/root/.hermes")

def sh(cmd):
    try:
        return subprocess.getoutput(cmd)
    except:
        return ""

def get_date():
    return sh("date '+%Y-%m-%d %H:%M:%S MSK'")

def build_report():
    now = get_date()

    # ========== СЕРВИСЫ systemd ==========
    svc_output = sh("systemctl list-units --type=service --all 2>/dev/null | grep -E 'zina|router|telegram|caddy|hermes-gateway|hermes-gc|hermes-web|sync|backup' | awk '{print \"    \" $1 \" [\" $3 \"]\"}'")
    svc_lines = [l for l in svc_output.split('\n') if l.strip()]

    # ========== ПОРТЫ ==========
    ports = sh("ss -tlnp 2>/dev/null | grep -E '8001|8002|8003|8005|8642|8901|6333|6379|443|80|2222|5000' | sort")

    # ========== DOCKER ==========
    docker = sh("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")

    # ========== БАЗЫ ДАННЫХ ==========
    dbs = sh("find /opt/zinaida -maxdepth 4 -name '*.db' -not -path '*backup*' -not -path '*__pycache__*' -not -path '*.bak*' -not -path '*.bak_*' -not -path '*node_modules*' -not -path '*.git*' -not -path '*lsp*' 2>/dev/null | sort")
    db_count = len([l for l in dbs.split('\n') if l.strip()])

    # ========== НАВЫКИ ==========
    skill_count = 0
    skill_categories = {}
    for root, dirs, files in os.walk(str(SKILLS_DIR)):
        if 'SKILL.md' in files:
            skill_count += 1
            cat = os.path.basename(os.path.dirname(root))
            name = os.path.basename(root)
            if cat not in skill_categories:
                skill_categories[cat] = []
            skill_categories[cat].append(name)
    
    skills_summary = ""
    for cat in sorted(skill_categories.keys()):
        names = skill_categories[cat]
        skills_summary += f"  📂 {cat}/ — {len(names)} навыков\n"
        for n in names[:5]:
            skills_summary += f"    • {n}\n"
        if len(names) > 5:
            skills_summary += f"    ... и ещё {len(names)-5}\n"

    # ========== СКРИПТЫ ==========
    scripts = sh("find /opt/zinaida/scripts -maxdepth 1 \\( -name '*.py' -o -name '*.sh' \\) 2>/dev/null | sort")
    script_list = [s.strip() for s in scripts.split('\n') if s.strip() and '/' in s]
    script_names = [s.rsplit('/', 1)[-1] for s in script_list]

    # ========== РОУТЕРЫ ==========
    routers = sh("ls /opt/zinaida/meta_agent/*router*.py /opt/zinaida/meta_agent/*proxy*.py 2>/dev/null | grep -v '.bak' | grep -v '__pycache__'")
    
    # ========== ПРОВАЙДЕРЫ из конфига ==========
    config_path = HERMES_DIR / "config.yaml"
    providers_info = ""
    if config_path.exists():
        content = config_path.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')
        in_prov = False
        for l in lines:
            if l.strip() == 'providers:':
                in_prov = True
                continue
            if in_prov:
                if l.strip().startswith('credential') or l.strip().startswith('toolsets') or l.strip().startswith('max_'):
                    break
                if 'api:' in l or 'name:' in l or 'default_model:' in l or 'model:' in l:
                    providers_info += f"    {l.strip()}\n"

    # ========== ПРОЕКТЫ ==========
    projects_main = sh("ls -d /opt/zinaida/projects/*/ 2>/dev/null")
    projects_inbox = sh("ls -d /opt/zinaida/inbox/PROJECTS/*/ 2>/dev/null")
    
    # Otnoshenya детально
    otnoshenya_files = sh("find /opt/zinaida/projects/Otnoshenya -maxdepth 1 -type f -name '*.md' -o -name '*.txt' 2>/dev/null | sort")
    otnoshenya_dirs = sh("ls -d /opt/zinaida/projects/Otnoshenya/*/ 2>/dev/null")

    # ========== ПИСАТЕЛЬ ==========
    pisatel_files = sh("find /opt/zinaida/projects/Otnoshenya/pisatel -type f -not -name 'drafts/*' 2>/dev/null | sort | head -20")

    # ========== VK ==========
    vk_bots = sh("find /opt/zinaida -maxdepth 3 -type f \\( -name '*vk_bot*' -o -name '*VK*' -o -name '*vk_public*' \\) -not -path '*__pycache__*' -not -path '*.bak*' -not -path '*.jpg' -not -path '*.png' 2>/dev/null | sort")

    # ========== TELEGRAM ==========
    tg_files = sh("find /opt/zinaida/telegram_bot -type f -not -path '*__pycache__*' -not -name '*.log' -not -name '*.bak*' 2>/dev/null | sort")

    # ========== GROUP CHAT ==========
    gc_agents = sh("find /opt/zinaida/scripts -name 'gc_*' -not -path '*__pycache__*' 2>/dev/null | sort")
    gc_svcs = sh("systemctl list-units --type=service --all 2>/dev/null | grep 'gc-' | awk '{print \"    \" $1 \" [\" $3 \"]\"}'")

    # ========== CHARACTER ==========
    char_files = sh("find /opt/zinaida/character -type f -not -path '*__pycache__*' 2>/dev/null | sort | head -15")

    # ========== DESIGN ==========
    design_generated = sh("find /opt/zinaida/design/generated -maxdepth 1 -type f -name '*.png' -o -name '*.jpg' 2>/dev/null | wc -l")
    design_approved = sh("find /opt/zinaida/design/approved -type f 2>/dev/null | wc -l")
    design_passport = sh("find /opt/zinaida/design/passport -type f -not -path '*__pycache__*' 2>/dev/null | wc -l")

    # ========== .env ФАЙЛЫ ==========
    env_files = sh("find / -maxdepth 4 -name '.env' -not -path '*/proc/*' -not -path '*/sys/*' -not -path '*node_modules*' -not -path '*lsp/*' -not -path '*docker/*' -not -path '*backup*' 2>/dev/null | sort")

    # ========== MEMORY ==========
    mem0_check = sh("curl -s http://127.0.0.1:6333/collections 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(f'    📦 {c}: {v[\\\"vectors_count\\\"]} vectors') for c,v in d.get('result',{}).get('collections',{}).items()]\" 2>/dev/null")

    # ========== ТРИГГЕРЫ ==========
    triggers = sh("grep -n 'ТРИГГЕР «' /opt/zinaida/AGENTS.md 2>/dev/null | sed 's/.*ТРИГГЕР/  🚩 ТРИГГЕР/'")

    # ========== СБОРКА ==========
    report = f"""══════════════════════════════════════════════════════════════════════
  СИСТЕМА ПЕРЕНОС v2.0
  ПОЛНЫЙ ИНВЕНТАРЬ СИСТЕМЫ ЗИНАИДЫ
  Сформирован: {now}
══════════════════════════════════════════════════════════════════════

ЧТО ЭТО ТАКОЕ?
───────────────
Полный дамп всей AI-системы «Зинаида». Все компоненты, триггеры, 
навыки, проекты, сервисы, память и железные протоколы.

При первом слове «перенос» от Олега — показать этот дамп.
Олег решает ЧТО и КОМУ передавать.
Для нового агента — навык содержит интерактивную установку.

────────────────────────────────────────────────────────────────────
1. ДНК И ЛИЧНОСТЬ
────────────────────────────────────────────────────────────────────
Файлы в /root/.hermes/:
  SOUL.md     — ядро персонажа (ДНК Зинаиды, стиль «Шквальный», 7 слоёв)
  AGENTS.md   — операционные правила (+40 триггеров на первое слово)
  MEMORY.md   — долговременная память и заметки
  USER.md     — профиль Олега
  ANTI_PATTERNS.md — чёрный список: что нельзя делать никогда

────────────────────────────────────────────────────────────────────
2. ТРИГГЕРЫ (первое слово в чате = команда)
────────────────────────────────────────────────────────────────────
{triggers}

────────────────────────────────────────────────────────────────────
3. ИНФРАСТРУКТУРА
────────────────────────────────────────────────────────────────────

⚙️ systemd сервисы ({len(svc_lines)}):
{chr(10).join(svc_lines)}

🔌 Порты:
{ports}

🐳 Docker:
{docker}

📡 Провайдеры (из config.yaml):
{providers_info}

🔄 Роутеры (активные .py, без бэкапов):
{routers}

🔑 .env файлы (ключи/токены):
{env_files}

────────────────────────────────────────────────────────────────────
4. НАВЫКИ ({skill_count} шт.)
────────────────────────────────────────────────────────────────────
{skills_summary}

────────────────────────────────────────────────────────────────────
5. БАЗЫ ДАННЫХ ({db_count} шт.)
────────────────────────────────────────────────────────────────────
{dbs}

────────────────────────────────────────────────────────────────────
6. ПРОЕКТЫ
────────────────────────────────────────────────────────────────────

Главные:
{projects_main}{projects_inbox}

Otnoshenya (контент-завод):
  Директории: {otnoshenya_dirs.replace(chr(10), ' ')}
  Файлы: {len(otnoshenya_files.split(chr(10)))}

Писатель (17 файлов):
{pisatel_files}

────────────────────────────────────────────────────────────────────
7. СКРИПТЫ ({len(script_list)} шт. в /opt/zinaida/scripts/)
────────────────────────────────────────────────────────────────────
{chr(10).join('  • ' + s for s in sorted(script_names))}

────────────────────────────────────────────────────────────────────
8. TELEGRAM И GROUP CHAT
────────────────────────────────────────────────────────────────────

Telegram-бот:
{tg_files}

Group Chat агенты ({len(gc_agents.split(chr(10)))}):
{gc_agents}

GC systemd сервисы:
{gc_svcs}

────────────────────────────────────────────────────────────────────
9. VK (VKontakte)
────────────────────────────────────────────────────────────────────
{vk_bots}

────────────────────────────────────────────────────────────────────
10. CHARACTER, PASSPORT И ДИЗАЙН
────────────────────────────────────────────────────────────────────

Character docs:
{char_files}

Design:
  • Сгенерировано изображений: {design_generated}
  • Утверждено: {design_approved}
  • Passport: {design_passport} файлов
  • GIF активации: /opt/zinaida/design/system_activate.gif
  • GIF переноса: /opt/zinaida/design/transfer_activate.gif
  • Стили: magazine_covers, quotes, scenes
  • Референсы: EGO_STRAKH, GPT_IMAGE_2, LoRA, Nano Banana

Voice Assistant:
  /opt/zinaida/voice_assistant/server.py
  /opt/zinaida/voice_assistant/index.html

────────────────────────────────────────────────────────────────────
11. ПАМЯТЬ (все уровни)
────────────────────────────────────────────────────────────────────

Mem0 (Qdrant 6333):
{mem0_check}

Holographic (SQLite): /root/.hermes/memory_store.db
fact_store: 57+ фактов с entity resolution
MEMORY.md + USER.md: профили

Базы знаний:
  phases.db (41 фаза отношений)
  smm_rag.db (3975 записей, FTS)
  analytics.db (метрики, EMA)
  content_rotation.db (ротация контента)
  smm_factory.db (фабрика постов)
  puls_validation.db (пульс-валидация)
  И ещё 20+ БД

────────────────────────────────────────────────────────────────────
12. ЖЕЛЕЗНЫЕ ПРОТОКОЛЫ (НЕ НАРУШАТЬ)
────────────────────────────────────────────────────────────────────
  🚫 Правило №0 (обещания) — сказала → делаю до конца
  🚫 Правило тестирования — 3 проверки перед «готово»
  🧠 Memory-First Protocol — проверять память перед действием
  🔧 System-Guarantee Protocol — 13 точек внедрения
  🏗️ Production-Change Protocol — бэкап → тест → интеграция
  🚫 ЗАПРЕЩЕНО редактировать production сторонними инструментами
  🚫 ЗАПРЕЩЁН MOA (категорически, навсегда)
  🚫 ЗАПРЕЩЁН мат в разговоре с Олегом
  🚫 ЗАПРЕЩЕНО: «тело сказало/организм», «сохрани и отправь подруге»
  🚫 ЗАПРЕЩЕНО: писать @username, ссылки на ботов — только «ссылка в шапке профиля»
  🚫 ЗАПРЕЩЕНО трогать роутер 8005 (Олег, 13.07.2026)
  🚫 n8n убит — Docker daemon-level resurrection, не восстанавливать

────────────────────────────────────────────────────────────────────
13. ДЛЯ НОВОГО АГЕНТА
────────────────────────────────────────────────────────────────────

При передаче — агент проводит ИНТЕРАКТИВНУЮ УСТАНОВКУ:

ШАГ 1 — Telegram: «Нужен свой бот. Зарегистрируй через @BotFather, дай токен.»
ШАГ 2 — Темы: «Что будешь исследовать? Консилиум настрою под тебя.»
ШАГ 3 — DeepSeek: «Ключ с api.deepseek.com. Принесёшь — подключу роутер 8003.»
ШАГ 4 — GitHub: «Куда выгрузить? Дай ссылку на репозиторий.»
ШАГ 5 — Выбор: «Что нужно? Контент-завод? Аналитика? Планировщик? VK?»
ШАГ 6 — Финало: Telegram ❌ | DeepSeek ❌ | GitHub ❌ | Темы ❌ | Выбор ❌ (0%)

ВАЖНО: НЕ копировать настройки Зинаиды. Спросить у пользователя.

══════════════════════════════════════════════════════════════════════
  ✅ ИТОГО: {skill_count} навыков, {db_count} БД, {len(svc_lines)} сервисов, {len(script_list)} скриптов
══════════════════════════════════════════════════════════════════════
"""
    return report

# ========== MAIN ==========
if __name__ == "__main__":
    output_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i+1 < len(sys.argv):
            output_file = sys.argv[i+1]
    
    report = build_report()
    
    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding='utf-8')
        print(f"✅ Отчёт сохранён: {out_path}")
    else:
        default_path = OUT_DIR / f"transfer_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        default_path.write_text(report, encoding='utf-8')
        print(f"✅ Отчёт сохранён: {default_path}")
    
    sha = hashlib.sha256(report.encode()).hexdigest()[:16]
    print(f"📝 Контрольная сумма: {sha}")
    print(f"📊 Размер: {len(report)} символов, {len(report.splitlines())} строк")
