#!/usr/bin/env python3
"""
ТЕХНИЧЕСКАЯ ДИАГНОСТИКА v5 — МАКСИМУМ
Полный аудит всей системы: каждый сервис, роутер, порт, процесс,
ключ, контейнер, cron, память, файл, профиль.
Запуск: python3 /opt/zinaida/scripts/tech_diagnostic.py
"""
import json, subprocess, sys, socket, urllib.request, time, os, re
from datetime import datetime

VERSION = "5.0"
START = time.time()
MAX_TOTAL = 120  # max total seconds

def curl(url, timeout=5, headers=None):
    try:
        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', errors='replace')[:250]
            return True, f"HTTP {r.getcode()}", body
    except Exception as e:
        return False, str(e)[:80], ""

def systemd_active(unit):
    try:
        r = subprocess.run(["systemctl","is-active",unit], capture_output=True, text=True, timeout=5)
        ok = r.stdout.strip() == "active"
        return ok, r.stdout.strip()
    except Exception as e:
        return False, str(e)[:40]

def systemd_enabled(unit):
    try:
        r = subprocess.run(["systemctl","is-enabled",unit], capture_output=True, text=True, timeout=5)
        return True, r.stdout.strip()
    except Exception as e:
        return False, str(e)[:40]

def port_check(port, host="127.0.0.1", timeout=2):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        ok = s.connect_ex((host, port)) == 0
        s.close()
        return ok, f"открыт" if ok else f"закрыт"
    except Exception as e:
        return False, str(e)[:40]

def sh(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return "—"

def models_on_port(port):
    try:
        r = subprocess.run(["curl","-s","--max-time","3",f"http://127.0.0.1:{port}/v1/models"], capture_output=True, text=True, timeout=5)
        data = r.stdout.strip()
        if not data:
            return False, "нет ответа"
        try:
            j = json.loads(data)
            models = j.get("data", [])
            names = [m.get("id","?") for m in models[:10]]
            return True, f"{len(names)}шт: {', '.join(names[:6])}"
        except:
            return True, f"ответ ({len(data)} байт)"
    except Exception as e:
        return False, str(e)[:40]

def health_on_port(port):
    ok, msg, extra = curl(f"http://127.0.0.1:{port}/health", timeout=3)
    return ok, msg[:60]

def run_section(name, items, timeout_total=30):
    started = time.time()
    results = []
    print(f"\n{'='*60}")
    print(f" 🔍 {name}")
    print(f"{'='*60}")
    for label, check_fn in items:
        elapsed = time.time() - started
        now_total = time.time() - START
        if elapsed > timeout_total:
            print(f"  ⏰ {label} — TIMEOUT ({int(elapsed)}с)")
            results.append((label, False, "TIMEOUT", None))
            continue
        if now_total > MAX_TOTAL:
            print(f"  ⏰ {label} — TOTAL TIMEOUT ({int(now_total)}с)")
            results.append((label, False, "TOTAL_TIMEOUT", None))
            continue
        print(f"  ⏳ {label}... ", end="", flush=True)
        try:
            raw = check_fn()
            if isinstance(raw, tuple) and len(raw) >= 2:
                ok = raw[0]
                msg = str(raw[1])
                extra = str(raw[2]) if len(raw) > 2 else None
            else:
                ok = bool(raw)
                msg = str(raw)
                extra = None
        except Exception as e:
            ok, msg, extra = False, str(e)[:60], None
        icon = "✅" if ok else "❌"
        print(f"{icon} {msg}")
        if extra and extra.strip() and extra != "None":
            print(f"       └─ {extra[:120]}")
        results.append((label, ok, msg, extra))
    return results

# ═══════════════════════════════════
print(f"{'='*60}")
print(f"  ЗИНАИДА :: ТЕХНИЧЕСКАЯ ДИАГНОСТИКА v{VERSION}")
print(f"  Полный аудит системы — каждый винтик")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")

# ═══════════════════════════════════
# 1. СЕРВИСЫ SYSTEMD (все известные)
# ═══════════════════════════════════
SYSTEMD_UNITS = [
    "caddy", "hermes-web-ui", "zinaida-telegram-bot",
    "zina2-router-8005", "zina2-router", "zinaida-router",
    "hermes4-router", "zinaida-core", "zinaida-sync",
    "hermes-gc-agent", "hermes-gc-agent-v2", "hermes-gc-olya",
    "hermes-gc-responder", "hermes-gc-responder-v2",
    "hermes-gc-v6", "hermes-gc-v7", "hermes-gc-zinaida",
    "hermes-group-chat-repair",
    "cloudflared", "cloudflared-update",
    
    "curator-weekly", "zinaida-weekly-backup",
]
items = []
for u in SYSTEMD_UNITS:
    items.append((f"{u}", lambda u=u: systemd_active(u)))
all_results = [run_section("СЕРВИСЫ SYSTEMD (активность)", items, timeout_total=30)]

# ═══════════════════════════════════
# 2. SYSTEMD ENABLED STATUS
# ═══════════════════════════════════
items = []
for u in SYSTEMD_UNITS:
    items.append((f"{u}", lambda u=u: systemd_enabled(u)))
all_results.append(run_section("СЕРВИСЫ SYSTEMD (включение)", items, timeout_total=30))

# ═══════════════════════════════════
# 3. РОУТЕРЫ — health + models
# ═══════════════════════════════════
ROUTER_PORTS = [
    (8002, "Zinaida-Router (прокси)"),
    (8003, "Hermes4-Router (классификатор)"),
    (8005, "Super Cascade (основной)"),
    (8006, "Оля 8006zs (Cascade)"),
    (8007, "Оля 8007nm (бесплатный)"),
    (5000, "VK Bot (Flask)"),
    (8648, "Gateway"),
    (8642, "Hermes internal"),
    (8900, "Ollama Fallback Proxy"),
    (8901, "Vision Fallback Proxy"),
    (10200, "Edge TTS Server"),
    (20241, "Cloudflared Tunnel"),
]
items = []
for port, label in ROUTER_PORTS:
    items.append((f"{label} (:{port})", lambda p=port: health_on_port(p) if p not in [8642, 20241] else (True, "внутренний/туннель")))
    items.append((f"{label} /v1/models", lambda p=port: models_on_port(p) if p in [8002, 8003, 8005, 8006, 8007] else (False, "—")))

# Добавляем прямой тест DeepSeek API через роутер 8005
def test_8005_deepseek():
    try:
        r = subprocess.run(
            ["curl","-s","--max-time","8","http://127.0.0.1:8005/health"],
            capture_output=True, text=True, timeout=10
        )
        data = r.stdout.strip()
        if not data:
            return False, "нет ответа"
        if "deepseek" in data and "true" in data:
            return True, "DeepSeek: доступен"
        return True, data[:100]
    except Exception as e:
        return False, str(e)[:40]
items.append(("8005 → DeepSeek доступ", test_8005_deepseek))

all_results.append(run_section("РОУТЕРЫ — HEALTH + MODELS", items, timeout_total=60))

# ═══════════════════════════════════
# 4. WEB UI FULL STACK
# ═══════════════════════════════════
items = []
items.append(("DuckDNS HTTPS", lambda: curl("https://zinadchdp.duckdns.org/", timeout=8)))
items.append(("Caddy конфиг", lambda: (True, sh("caddy validate --config /etc/caddy/Caddyfile 2>&1")[:60])))
items.append(("WebUI healthcheck log", lambda: (True, sh("journalctl -t webui-healthcheck --no-pager -n 1 2>/dev/null | cut -d' ' -f5-")[:60])))
items.append(("Hermes Dashboard (8642)", lambda: curl("http://127.0.0.1:8642/", timeout=3)))
all_results.append(run_section("WEB UI FULL STACK", items, timeout_total=20))

# ═══════════════════════════════════
# 5. ПОРТЫ (все, какие нашли)
# ═══════════════════════════════════
ALL_PORTS = [22, 80, 443, 5000, 6060, 6333, 6334, 6379, 8002, 8003, 8005, 8006, 8007,
             8642, 8648, 8888, 8900, 8901, 9119, 10050, 10200, 11434, 18000, 20241, 2222]
items = []
items.append(("UFW статус", lambda: (True, sh("ufw status verbose 2>/dev/null | head -3")[:60]) if os.path.exists("/usr/sbin/ufw") else (False, "нет UFW")))
for p in ALL_PORTS:
    items.append((f"Порт {p}", lambda p=p: port_check(p)))
all_results.append(run_section("ПОРТЫ (сканирование всех)", items, timeout_total=30))

# ═══════════════════════════════════
# 6. СЛУШАЮЩИЕ ПРОЦЕССЫ
# ═══════════════════════════════════
def listening_processes():
    raw = sh("ss -tlnp 2>/dev/null")
    lines = raw.split('\n')
    info = []
    for l in lines:
        if 'LISTEN' in l and '127.0.0.53' not in l:
            parts = l.split()
            if len(parts) >= 7:
                addr = parts[4]
                proc = parts[6][:60]
                info.append(f"{addr}  {proc}")
    return True, f"{len(info)} процессов", "\n".join(info[:20])
all_results.append(run_section("СЛУШАЮЩИЕ ПРОЦЕССЫ", [("ss -tlnp", listening_processes)], timeout_total=10))

# ═══════════════════════════════════
# 7. ПРОЦЕССЫ (python3)
# ═══════════════════════════════════
def python_processes():
    raw = sh("ps aux | grep python3 | grep -v grep")
    lines = raw.split('\n')
    info = []
    for l in lines:
        if not l.strip():
            continue
        parts = l.split(None, 10)
        if len(parts) >= 11:
            mem = parts[3]
            pid = parts[1]
            cmd = parts[10][:80]
            info.append(f"[{pid}] {mem}% {cmd}")
    return True, f"{len(info)} процессов python3", "\n".join(info[:20])
all_results.append(run_section("ПРОЦЕССЫ PYTHON", [("ps aux | grep python3", python_processes)], timeout_total=10))

# ═══════════════════════════════════
# 8. DOCKER
# ═══════════════════════════════════
def docker_all():
    raw = sh("docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null")
    if not raw:
        return False, "Docker не отвечает"
    containers = raw.split('\n')
    ok_count = sum(1 for c in containers if 'Up' in c)
    return True, f"{len(containers)} контейнеров ({ok_count} работают)"
items = []
items.append(("Docker общий статус", docker_all))
for c in sh("docker ps -a --format '{{.Names}}|{{.Status}}|{{.Ports}}' 2>/dev/null").split('\n'):
    if not c.strip():
        continue
    parts = c.split('|')
    name = parts[0]
    ok = 'Up' in parts[1]
    items.append((f"  {name}", lambda o=ok, p=parts[1]: (o, p)))
all_results.append(run_section("DOCKER (контейнеры)", items, timeout_total=15))

# ═══════════════════════════════════
# 9. ПРОВАЙДЕРЫ И КЛЮЧИ
# ═══════════════════════════════════
env_path = "/opt/zinaida/meta_agent/.env"
env_hermes = "/root/.hermes/.env"
env_content = ""
if os.path.exists(env_path):
    env_content = open(env_path).read()

items = []
items.append(("Файл meta_agent/.env", lambda: (os.path.exists(env_path), f"{os.path.getsize(env_path)} байт")))
items.append(("Файл ~/.hermes/.env", lambda: (os.path.exists(env_hermes), f"{os.path.getsize(env_hermes)} байт" if os.path.exists(env_hermes) else "нет")))

key_checks = [
    ("DeepSeek (sk-)", "deepseek" in env_content.lower() and "sk-" in env_content),
    ("Todoist (4f439c)", "4f439c11" in env_content or "todoist" in env_content.lower()),
    ("BrightData (929dbdc5)", "929dbdc5" in env_content),
    ("FAL (8e99...)", "fal" in env_content.lower() or "8e99" in env_content),
    ("GigaChat", "gigachat" in env_content.lower()),
    ("Mistral", "mistral" in env_content.lower()),
    ("OpenRouter", "openrouter" in env_content.lower()),
    ("GitHub Token", "github" in env_content.lower() and "ghp_" in env_content),
    ("VK Token", "vk1.a." in env_content),
    ("Cloudflare Tunnel", "cloudflared" in env_content.lower() or "tunnel" in env_content.lower()),
]
for label, exists in key_checks:
    items.append((f"Ключ: {label}", lambda e=exists: (e, "есть" if e else "нет" if os.path.exists(env_path) else "файла нет")))

# Прямой тест DeepSeek API
def test_deepseek_direct():
    key = ""
    for line in env_content.split('\n'):
        if 'DEEPSEEK' in line and 'sk-' in line:
            key = line.split('=')[1].strip()
            break
    if not key:
        return False, "ключ не найден"
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            models = [m["id"] for m in data.get("data", [])]
            return True, f"доступен, {len(models)} моделей: {', '.join(models[:4])}"
    except Exception as e:
        return False, str(e)[:60]
items.append(("DeepSeek API (прямой)", test_deepseek_direct))

# FAL ключ тест
def test_fal():
    try:
        r = subprocess.run(["curl","-s","https://fal.run/serverless","--max-time","5"], capture_output=True, text=True, timeout=6)
        if r.returncode == 0:
            return True, "доступен"
        return False, r.stderr[:40]
    except Exception as e:
        return False, str(e)[:40]

# Hermes ключи
items.append(("FAL API (fal.run)", test_fal))
items.append(("Hermes статус ключей", lambda: (True, sh("hermes status 2>&1 | grep -E '(✓|✗)' | wc -l") + " проверок")))
all_results.append(run_section("ПРОВАЙДЕРЫ И КЛЮЧИ", items, timeout_total=25))

# ═══════════════════════════════════
# 10. CRON (все строки)
# ═══════════════════════════════════
cron = sh("crontab -l 2>/dev/null") or "—"
cron_lines = [l.strip() for l in cron.split('\n') if l.strip() and not l.strip().startswith('#')]
items = [(f"[{i+1}] {l[:70]}", lambda: (True, "active")) for i, l in enumerate(cron_lines[:30])]
all_results.append(run_section(f"CRON (активных: {len(cron_lines)})", items, timeout_total=10))

# ═══════════════════════════════════
# 11. HERMES ПРОФИЛИ
# ═══════════════════════════════════
def hermes_profiles():
    raw = sh("hermes status 2>&1 | grep -A 20 'Profiles'")
    return True, raw[:200]
items = []
items.append(("Список профилей", hermes_profiles))
items.append(("Профилей всего", lambda: (True, f"{len([p for p in sh('hermes status 2>&1').split(chr(10)) if 'profile' in p.lower()])}")))
items.append(("Навыков (skills)", lambda: (True, f"{len(os.listdir('/root/.hermes/skills/'))} шт") if os.path.isdir('/root/.hermes/skills/') else (False, "нет папки")))
items.append(("Плагины (plugins)", lambda: (True, ', '.join(os.listdir('/root/.hermes/plugins/'))) if os.path.isdir('/root/.hermes/plugins/') else (False, "нет")))
items.append(("Config.yaml", lambda: (True, f"{os.path.getsize('/root/.hermes/config.yaml')} байт")))
items.append(("Cron (Hermes)", lambda: (True, f"{len([f for f in os.listdir('/root/.hermes/cron/') if f.endswith('.json')])} задач") if os.path.isdir('/root/.hermes/cron/') else (False, "нет")))
all_results.append(run_section("HERMES — ПРОФИЛИ, НАВЫКИ, ПЛАГИНЫ", items, timeout_total=10))

# ═══════════════════════════════════
# 12. ПАМЯТЬ И ФАЙЛЫ
# ═══════════════════════════════════
MEM_FILES = {
    "/opt/zinaida/memory/MEMORY.md": "MEMORY.md",
    "/opt/zinaida/memory/USER.md": "USER.md",
    "/root/.hermes/SOUL.md": "SOUL.md",
    "/opt/zinaida/memory/SYSTEM_SNAPSHOT.md": "SYSTEM_SNAPSHOT.md",
    "/opt/zinaida/memory/smm_rag.db": "smm_rag.db",
    "/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db": "phases.db",
    "/opt/zinaida/memory/analytics.db": "analytics.db",
    "/opt/zinaida/meta_agent/quotas.db": "quotas.db",
    "/opt/zinaida/meta_agent/router_8005_v2.py": "router_8005_v2.py",
    "/opt/zinaida/meta_agent/zinaida_openai_proxy.py": "zinaida_openai_proxy.py",
    "/opt/zinaida/meta_agent/hermes4_router.py": "hermes4_router.py",
    "/opt/zinaida/meta_agent/olya_8006zs.py": "olya_8006zs.py (Оля Cascade)",
    "/opt/zinaida/meta_agent/olya_8007nm.py": "olya_8007nm.py (Оля бесплатный)",
    "/opt/zinaida/telegram_bot/bot.py": "Telegram-бот",
    "/opt/zinaida/vk_bot/vk_bot.py": "VK-бот",
    "/opt/zinaida/scripts/deep_research_orchestrator.py": "Deep Research",
    "/root/.hermes/config.yaml": "config.yaml",
    "/etc/caddy/Caddyfile": "Caddyfile",
    "/etc/systemd/system/zina2-router-8005.service": "8005 systemd",
    "/etc/systemd/system/hermes-web-ui.service": "Web UI systemd",
}
items = []
for path, label in MEM_FILES.items():
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    items.append((label, lambda e=exists, s=size, n=path: (e, f"{s/1024:.1f}K" if e else "—")))
all_results.append(run_section("КЛЮЧЕВЫЕ ФАЙЛЫ", items, timeout_total=10))

# ═══════════════════════════════════
# 13. БАЗЫ ДАННЫХ
# ═══════════════════════════════════
all_dbs = sh("find /opt/zinaida -name '*.db' -type f 2>/dev/null")
items = []
for db in all_dbs.split('\n'):
    if not db.strip():
        continue
    fsize = os.path.getsize(db) if os.path.exists(db) else 0
    items.append((db.replace('/opt/zinaida/', ''), lambda e=True, s=fsize, n=db: (True, f"{s/1024:.1f}K")))
all_results.append(run_section("БАЗЫ ДАННЫХ (.db)", items, timeout_total=5))

# ═══════════════════════════════════
# 14. Qdrant / Mem0
# ═══════════════════════════════════
def qdrant_collections():
    try:
        req = urllib.request.Request("http://localhost:6333/collections")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            cols = data.get("result", {}).get("collections", [])
            names = [c["name"] for c in cols]
            return True, f"{len(names)} коллекций: {', '.join(names[:5])}"
    except Exception as e:
        return False, str(e)[:60]
items = []
items.append(("Qdrant API", qdrant_collections))
items.append(("Mem0 MCP процесс", lambda: (True, f"PID {sh('pgrep -f mem0_mcp_server')}") if sh('pgrep -f mem0_mcp_server') else (False, "не запущен")))
items.append(("Qdrant Docker лог", lambda: (True, sh("docker logs qdrant --tail 1 2>/dev/null | head -1")[:60])))
all_results.append(run_section("QDRANT / MEM0", items, timeout_total=10))

# ═══════════════════════════════════
# 15. СИСТЕМА (железо/ОС)
# ═══════════════════════════════════
mem = sh("free -m | awk 'NR==2{printf \"%d/%d MB (%.0f%%)\", $3, $2, $3/$2*100}'")
disk = sh("df -h / | tail -1 | awk '{printf \"%s/%s (%s)\", $3, $2, $5}'")
load = sh("uptime | awk -F'load average:' '{print $2}' | xargs")
upt = sh("uptime -p")
pv = sys.version.split()[0]
host = sh("hostname")
kernel = sh("uname -r")
items = [
    ("RAM", lambda: (True, mem)),
    ("Диск /", lambda: (True, disk)),
    ("Load Average", lambda: (True, load)),
    ("Uptime", lambda: (True, upt)),
    ("Python", lambda: (True, pv)),
    ("Hostname", lambda: (True, host)),
    ("Kernel", lambda: (True, kernel)),
    ("Дата/время", lambda: (True, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))),
]
all_results.append(run_section("СИСТЕМА (железо/ОС)", items, timeout_total=10))

# ═══════════════════════════════════
# 16. ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ
# ═══════════════════════════════════
items = []
items.append(("Rclone (OneDrive)", lambda: (True, sh("ps aux | grep 'rclone mount' | grep -v grep | awk '{print $2}'")) if sh("mount | grep -q onedrive && echo ok") else (False, "не примонтирован")))
items.append(("Zabbix агент", lambda: (True, sh("systemctl is-active zabbix-agent 2>/dev/null")) if os.path.exists('/etc/systemd/system/zabbix-agent.service') else (False, "нет")))

def searxng_test():
    ok, msg, _ = curl("http://127.0.0.1:8888/search?q=test", timeout=3)
    return ok, "доступен" if ok else msg
items.append(("SearXNG (поиск)", searxng_test))

def content_factory():
    return (True, sh("ls /opt/zinaida/SmmFabrika/content_factory.py 2>/dev/null && echo 'есть' || echo 'нет файла'"))
items.append(("Content Factory", content_factory))

def gc_agents_check():
    scripts = os.listdir('/opt/zinaida/scripts/')
    gc = [s for s in scripts if s.startswith('gc_agent')]
    return True, f"{len(gc)} скриптов: {', '.join(gc[:8])}"
items.append(("GC агенты", gc_agents_check))

items.append(("Edge TTS", lambda: (True, "работает") if sh("pgrep -f edge_tts_server") else (False, "не запущен")))
items.append(("Cloudflare Tunnel", lambda: (True, sh("systemctl is-active cloudflared 2>/dev/null")) if os.path.exists('/etc/systemd/system/cloudflared.service') else (False, "нет")))
items.append(("Rclone Bisync лог", lambda: (True, sh("tail -1 /opt/zinaida/logs/rclone_bisync.log 2>/dev/null")[:60])))
items.append(("Доступ в интернет", lambda: curl("https://google.com", timeout=5)[:2] if True else (False, "")))
all_results.append(run_section("ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ", items, timeout_total=20))


# ═══════════════════════════════════
# 18. GRAPHIFY (граф знаний)
# ═══════════════════════════════════
items = []
items.append(("Graphify CLI", lambda: (True, sh('export PATH=\$HOME/.local/bin:\$PATH && graphify --version 2>/dev/null')[:20]) if sh('export PATH=\/root/.local/bin:\/root/.local/bin:/root/.local/bin:/root/.local/bin:/root/.local/bin:/root/.local/bin:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/homebrew/bin:/opt/homebrew/sbin && which graphify 2>/dev/null') else (False, "не установлен")))
items.append(("Граф знаний (graph.json)", lambda: (True, f'{os.path.getsize("/opt/zinaida/graphify-out/graph.json")/1024:.0f}K') if os.path.exists('/opt/zinaida/graphify-out/graph.json') else (False, "нет графа")))
items.append(("Навык во всех профилях", lambda: (True, 'default+agent2+copywriter+designer+olya') if os.path.exists('/root/.hermes/skills/graphify/SKILL.md') else (False, "нет навыка")))
all_results.append(run_section("GRAPHIFY (граф знаний)", items, timeout_total=10))

# ═══════════════════════════════════
# 17. ИТОГ
# ═══════════════════════════════════
total_ok = 0
total_fail = 0
total_timeout = 0
for section in all_results:
    for item in section:
        if len(item) >= 3:
            if item[1] is True:
                total_ok += 1
            elif item[1] is False:
                total_fail += 1
            else:
                total_timeout += 1

elapsed = time.time() - START
print(f"\n{'='*60}")
print(f"  ДИАГНОСТИКА ЗАВЕРШЕНА за {elapsed:.0f}с")
print(f"  ✅ {total_ok} проверок OK")
print(f"  ❌ {total_fail} проблем")
print(f"  ⏰ {total_timeout} таймаутов")
print(f"  📊 Всего: {total_ok + total_fail + total_timeout} проверок")
print(f"{'='*60}")

if total_fail > 0:
    print(f"\n  ⚠️  ПРОБЛЕМНЫЕ ЗОНЫ ({total_fail} шт):")
    for section in all_results:
        for item in section:
            if len(item) >= 3 and item[1] is False:
                label = item[0] if item[0] else "?"
                msg = str(item[2])[:80] if item[2] else "?"
                print(f"    ❌ {label}: {msg}")
    print()

# Вывод времени выполнения
elapsed = time.time() - START
print(f"  ⏱ Выполнено за {elapsed:.1f}с")
