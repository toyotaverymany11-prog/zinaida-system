#!/usr/bin/env python3
"""
Zinaida Unified Agent Runtime
Замыкает контур: мониторинг → планирование → исполнение → проверка → саморемонт.
Безопасный, атомарный, с динамическим контекстом и мгновенным откатом.
"""
import os, sys, json, time, logging, subprocess, shutil, re, signal, requests
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RUNTIME] %(message)s")
logger = logging.getLogger(__name__)

CORE_URL = "http://127.0.0.1:8002/v1/chat/completions"
GATEWAY_URL = "http://127.0.0.1:8003/v1/chat/completions"
MEMORY_URL = "http://127.0.0.1:8002"
BACKUP_DIR = "/opt/zinaida/backups"
SANDBOX_DIR = "/opt/zinaida/sandbox"
META_DIR = "/opt/zinaida/meta_agent"
KB_PATH = f"{SANDBOX_DIR}/knowledge/provider_knowledge_base.md"
TASK_MASTER_PATH = "/opt/zinaida/dashboard/TASK_MASTER.md"
CHECK_INTERVAL = 90
MAX_CONTEXT_TOKENS = 7500
BLOCKED_FILES = ["zinaida_router.py", "agent_runtime.py", "atomic_deploy.py", "grigoriy_router.py"]
ALLOWED_CMDS_PATTERNS = [
    r"^systemctl (restart|start|stop|is-active|status) zinaida-[a-z\-]+$",
    r"^python3 /opt/zinaida/sandbox/scripts/[a-z_]+\.py.*$",
    r"^curl -s -m \d+ http://(localhost|127\.0\.0\.1):\d+/.*$",
    r"^curl -s -X POST https://api\.telegram\.org/bot.*$",
    r"^cat /opt/zinaida/(sandbox|configs|backups|logs|meta_agent|inbox)/.*$"
]
AUDIT_LOG = "/opt/zinaida/logs/runtime_audit.json"
RUNNING = True

def handle_signal(sig, frame):
    global RUNNING
    logger.info("Сигнал завершения. Останавливаю рантайм.")
    RUNNING = False

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def audit(action, details):
    entry = {"ts": time.time(), "action": action, "details": details}
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def is_cmd_allowed(cmd):
    return any(re.match(p, cmd.strip()) for p in ALLOWED_CMDS_PATTERNS)

def run_safe(cmd, timeout=15):
    if not is_cmd_allowed(cmd):
        res = {"ok": False, "error": "Blocked by allowlist", "cmd": cmd}
        audit("blocked", res)
        return res
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        res = {"ok": proc.returncode == 0, "code": proc.returncode, "out": proc.stdout[:500], "err": proc.stderr[:300]}
        audit("executed", res)
        return res
    except subprocess.TimeoutExpired:
        res = {"ok": False, "error": "Timeout", "cmd": cmd}
        audit("timeout", res)
        return res
    except Exception as e:
        res = {"ok": False, "error": str(e)[:200], "cmd": cmd}
        audit("crash", res)
        return res

def build_context(user_msg=""):
    parts = []
    try:
        if os.path.exists(TASK_MASTER_PATH):
            with open(TASK_MASTER_PATH, "r", encoding="utf-8") as f:
                parts.append(f"TASK_MASTER (фрагмент):\n{f.read()[:800]}")
    except Exception:
        pass
    try:
        if os.path.exists(KB_PATH):
            with open(KB_PATH, "r", encoding="utf-8") as f:
                parts.append(f"KNOWLEDGE BASE (фрагмент):\n{f.read()[:800]}")
    except Exception:
        pass
    try:
        tasks = []
        for st in ["executing", "stuck"]:
            r = requests.get(f"{MEMORY_URL}/memory/tasks?status={st}", timeout=3)
            if r.status_code == 200:
                tasks.extend(r.json().get("tasks", []))
        if tasks:
            lines = [f"- [{t['status'].upper()}] ID:{t['id']} | {t['title']}" for t in tasks[:4]]
            parts.append("АКТИВНЫЕ ЗАДАЧИ:\n" + "\n".join(lines))
    except Exception:
        pass
    ctx = "ПРОТОКОЛ АВТОНОМНОГО РАНТАЙМА:\n1. Вы единый контур. Наблюдайте, планируйте, исполняйте, проверяйте.\n2. При аномалии (пустой ответ, 502, таймаут, зависание) -> диагностируйте -> чините через sandbox/runtime -> отчитывайтесь.\n3. Контекст оптимизирован. Не дублируйте информацию. Отвечайте структурно.\n4. Ремонт кода: только через propose_patch -> compile -> dry-run -> deploy -> rollback при провале.\n5. В конце ответа СТРОГО одна строка JSON: {\"task_id\": <id>, \"status\": \"<executing|done|stuck>\", \"result\": \"<итог>\"}\n\n"
    ctx += "\n\n".join(parts)
    if user_msg:
        ctx += f"\n\nОПЕРАТОР: {user_msg[:500]}"
    return ctx[:MAX_CONTEXT_TOKENS]

def check_health():
    status = {"services_ok": True, "logical_ok": True, "errors": []}
    for svc in ["zinaida-gateway", "zinaida-core", "zinaida-memory", "zinaida-dashboard"]:
        try:
            res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
            if res.stdout.strip() != "active":
                status["services_ok"] = False
                status["errors"].append(f"Service down: {svc}")
        except Exception:
            status["errors"].append(f"Check failed: {svc}")
    try:
        r = requests.post(GATEWAY_URL, json={"messages": [{"role": "user", "content": "status"}], "stream": False}, timeout=20)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if not txt or len(txt) < 5 or "Запрос обработан" in txt or "System Error" in txt:
                status["logical_ok"] = False
                status["errors"].append("Logical anomaly: empty/fallback response")
        else:
            status["logical_ok"] = False
            status["errors"].append(f"Gateway HTTP {r.status_code}")
    except Exception as e:
        status["logical_ok"] = False
        status["errors"].append(f"Gateway unreachable: {str(e)[:80]}")
    return status

def propose_and_deploy_patch(filename, new_content):
    if filename in BLOCKED_FILES:
        return {"ok": False, "error": "File is in BLOCKED_FILES (core protection)"}
    sandbox_path = f"/opt/zinaida/sandbox/code_repair/{filename}"
    os.makedirs(os.path.dirname(sandbox_path), exist_ok=True)
    with open(sandbox_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    try:
        res = subprocess.run([sys.executable, "-m", "py_compile", sandbox_path], capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return {"ok": False, "error": f"Syntax: {res.stderr[:200]}"}
    except Exception as e:
        return {"ok": False, "error": f"Compile crash: {str(e)[:150]}"}
    target_path = os.path.join(META_DIR, filename)
    backup_path = os.path.join(BACKUP_DIR, f"{filename}.pre_repair_{int(time.time())}")
    try:
        shutil.copy2(target_path, backup_path)
        shutil.copy2(sandbox_path, target_path)
        audit("patch_deployed", {"file": filename, "backup": backup_path})
        return {"ok": True, "backup": backup_path}
    except Exception as e:
        return {"ok": False, "error": f"Deploy failed: {str(e)[:150]}"}

def rollback_patch(filename, backup_path):
    target_path = os.path.join(META_DIR, filename)
    try:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, target_path)
            audit("patch_rolled_back", {"file": filename, "backup": backup_path})
            return {"ok": True}
        return {"ok": False, "error": "Backup missing"}
    except Exception as e:
        return {"ok": False, "error": f"Rollback failed: {str(e)[:150]}"}

def main():
    logger.info("Unified Agent Runtime started. Closed-loop autonomy active.")
    while RUNNING:
        try:
            health = check_health()
            if not health["errors"]:
                time.sleep(CHECK_INTERVAL)
                continue
            logger.warning(f"Anomalies: {health['errors']}")
            audit("anomaly_detected", health["errors"])
            prompt = build_context(f"СИСТЕМНАЯ АНОМАЛИЯ: {', '.join(health['errors'])}. Диагностируй, предложи план, исполни через runtime, проверь результат.")
            try:
                resp = requests.post(CORE_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=45)
                if resp.status_code == 200:
                    txt = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info(f"Agent response: {txt[:200]}")
                    audit("agent_response", {"length": len(txt), "preview": txt[:150]})
                else:
                    logger.warning(f"Core HTTP {resp.status_code}")
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
            for svc in ["zinaida-core", "zinaida-gateway"]:
                if f"Service down: {svc}" in str(health["errors"]):
                    logger.info(f"Direct restart: {svc}")
                    run_safe(f"systemctl restart {svc}")
                    time.sleep(6)
            audit("cycle_complete", {"errors": health["errors"]})
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Runtime loop error: {e}. Sleeping 60s.")
            audit("runtime_error", str(e)[:200])
            time.sleep(60)

if __name__ == "__main__":
    main()
