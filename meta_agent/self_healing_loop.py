#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests, json, time, logging, subprocess, re, argparse
from execution_bridge import run_safe
from state_manager import create_snapshot, rollback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HEALER] %(message)s")
logger = logging.getLogger(__name__)

CORE_URL = "http://localhost:8000/v1/chat/completions"
SERVICES = ["zinaida-gateway", "zinaida-core", "zinaida-memory", "zinaida-dashboard"]
CHECK_INTERVAL = 60
MAX_FIX_ATTEMPTS = 3
COOLDOWN_FILE = "/opt/zinaida/logs/healer_cooldown.json"

def load_cooldown():
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE) as f: return json.load(f)
        except: pass
    return {"attempts": {}, "last_reset": time.time()}

def save_cooldown(data):
    try:
        with open(COOLDOWN_FILE, "w") as f: json.dump(data, f)
    except: pass

def check_health() -> list:
    failed = []
    for svc in SERVICES:
        try:
            res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
            if res.stdout.strip() != "active": failed.append(svc)
        except: failed.append(svc)
    return failed

def get_logs(svc: str, lines: int = 15) -> str:
    try:
        res = subprocess.run(["journalctl", "-u", svc, "--no-pager", "-n", str(lines)], capture_output=True, text=True, timeout=5)
        return res.stdout.strip()
    except: return "Log fetch failed"

def extract_json_from_llm(text: str) -> dict:
    if not text: return {}
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match: return {}
    try:
        data = json.loads(match.group())
        if isinstance(data, dict) and "commands" in data and "verify_command" in data:
            return data
    except: pass
    return {}

def ask_llm_for_fix(failed_services: list, logs: dict) -> dict:
    prompt = f"""
Системный сбой. Не работают сервисы: {', '.join(failed_services)}.
Логи:
{json.dumps(logs, ensure_ascii=False, indent=2)}

Твоя задача: проанализировать причину и вернуть СТРОГО JSON с планом восстановления.
Формат (ТОЛЬКО JSON, БЕЗ ТЕКСТА, БЕЗ MARKDOWN):
{{"reasoning": "<причина>", "commands": ["<команда 1>", "<команда 2>"], "verify_command": "<команда проверки>"}}

Разрешено: systemctl restart zinaida-*, python3 /opt/zinaida/sandbox/scripts/*.py, curl тесты, cp/ln конфигов.
Запрещено: rm, chmod, eval, внешние загрузки. Максимум 3 команды.
Если причина в конфиге или провайдере → добавь команду запуска песочницы или резолвера.
"""
    try:
        resp = requests.post(CORE_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=30)
        if resp.status_code == 200:
            txt = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return extract_json_from_llm(txt)
        else:
            logger.warning(f"Core HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Core unreachable: {e}")
    return {"reasoning": "LLM unavailable", "commands": [], "verify_command": ""}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    mode = "DRY-RUN" if args.dry_run else "LIVE"
    logger.info(f"🛡️ Self-Healing Loop started in {mode} mode.")
    cooldown = load_cooldown()
    
    while True:
        try:
            failed = check_health()
            if not failed:
                time.sleep(CHECK_INTERVAL)
                continue
                
            logger.warning(f"⚠️ Services down: {failed}")
            for svc in failed:
                if cooldown["attempts"].get(svc, 0) >= MAX_FIX_ATTEMPTS:
                    logger.error(f"🚫 Max attempts reached for {svc}. Escalating.")
                    continue
                    
            logs = {svc: get_logs(svc) for svc in failed}
            plan = ask_llm_for_fix(failed, logs)
            logger.info(f"🧠 LLM plan: {plan.get('reasoning', 'none')} | Commands: {len(plan.get('commands', []))}")
            
            if not plan.get("commands"):
                logger.info("No valid commands. Skipping cycle.")
                time.sleep(CHECK_INTERVAL)
                continue
                
            success = True
            for cmd in plan["commands"][:3]:
                logger.info(f"🔧 {'[DRY-RUN] Would run' if args.dry_run else 'Executing'}: {cmd}")
                if not args.dry_run:
                    res = run_safe(cmd)
                    if not res["ok"]:
                        logger.error(f"Command failed: {res.get('error')}")
                        success = False
                        break
                        
            time.sleep(5)
            verify = plan.get("verify_command", f"systemctl is-active {failed[0]}")
            logger.info(f"🔍 {'[DRY-RUN] Would verify' if args.dry_run else 'Verifying'}: {verify}")
            
            if not args.dry_run:
                v_res = run_safe(verify)
                if success and v_res["ok"] and "active" in v_res.get("out", ""):
                    logger.info("✅ Recovery successful. Creating snapshot.")
                    create_snapshot(reason=f"healer_fix_{','.join(failed)}")
                    for svc in failed: cooldown["attempts"][svc] = 0
                else:
                    logger.warning("⚠️ Recovery failed. Attempting rollback.")
                    for svc in failed:
                        cooldown["attempts"][svc] = cooldown["attempts"].get(svc, 0) + 1
                    try:
                        snaps = sorted(os.listdir("/opt/zinaida/backups/"))
                        if snaps: rollback(snaps[-1])
                    except: pass
                    
            save_cooldown(cooldown)
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Healer stopped by user.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Healer loop error: {e}. Sleeping 60s.")
            time.sleep(60)

if __name__ == "__main__":
    main()
