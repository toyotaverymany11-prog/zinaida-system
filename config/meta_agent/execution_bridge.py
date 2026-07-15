#!/usr/bin/env python3
import subprocess, json, sys, os, re, time, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXEC-BRIDGE] %(message)s")
logger = logging.getLogger(__name__)

ALLOWLIST_PATTERNS = [
    r"^systemctl (restart|start|stop|is-active|status) zinaida-[a-z]+$",
    r"^python3 /opt/zinaida/sandbox/scripts/[a-z_]+\.py.*$",
    r"^curl -s -m \d+ http://localhost:\d+/.*$",
    r"^cp /opt/zinaida/configs/versions/[a-z0-9_]+\.json /opt/zinaida/configs/active\.json$",
    r"^ln -sf /opt/zinaida/configs/versions/[a-z0-9_]+\.json /opt/zinaida/configs/active\.json$",
    r"^cat /opt/zinaida/(sandbox|configs|backups|logs)/.*$"
]
AUDIT_LOG = "/opt/zinaida/logs/healer_audit.json"

def audit(action, cmd, result):
    entry = {"ts": time.time(), "action": action, "cmd": cmd, "result": result}
    try:
        with open(AUDIT_LOG, "a") as f: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except: pass

def is_allowed(cmd: str) -> bool:
    return any(re.match(p, cmd.strip()) for p in ALLOWLIST_PATTERNS)

def run_safe(cmd: str, timeout: int = 15) -> dict:
    if not is_allowed(cmd):
        res = {"ok": False, "error": "Blocked by allowlist", "cmd": cmd}
        audit("blocked", cmd, res)
        return res
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        res = {"ok": proc.returncode == 0, "code": proc.returncode, "out": proc.stdout[:500], "err": proc.stderr[:300]}
        audit("executed", cmd, res)
        return res
    except subprocess.TimeoutExpired:
        res = {"ok": False, "error": "Timeout", "cmd": cmd}
        audit("timeout", cmd, res)
        return res
    except Exception as e:
        res = {"ok": False, "error": str(e)[:200], "cmd": cmd}
        audit("crash", cmd, res)
        return res

if __name__ == "__main__":
    print("✅ Execution Bridge loaded. Use run_safe(cmd) to execute.")
