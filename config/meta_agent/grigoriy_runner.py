#!/usr/bin/env python3
import os, sys, json, requests, subprocess, time
from datetime import datetime
from pathlib import Path

GRIGORIY_URL = "http://localhost:8002/generate"
HEALTH_URL = "http://localhost:8002/health"
MEMORY_DIR = Path("/opt/zinaida/memory/grigoriy")
LESSONS_FILE = MEMORY_DIR / "lessons_learned.md"
ERROR_LOG_FILE = MEMORY_DIR / "error_log.json"
MAX_RETRIES = 3

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] [Григорий] {msg}", flush=True)

def read_lessons(max_count=3):
    if not LESSONS_FILE.exists(): return ""
    try:
        with open(LESSONS_FILE, 'r', encoding='utf-8') as f: content = f.read()
        return "\n\n".join(f"## [{b}" for b in content.split('## [')[1:][-max_count:])
    except: return ""

def read_errors(max_count=3):
    if not ERROR_LOG_FILE.exists(): return []
    try:
        with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f: return json.load(f).get("errors", [])[-max_count:]
    except: return []

def check_health():
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        return r.status_code == 200
    except: return False

def call_grigoriy(task, lessons, errors):
    ctx = ""
    if lessons: ctx += f"\nОПЫТ:\n{lessons}"
    if errors: ctx += "\nОШИБКИ:\n" + "\n".join(e.get('error','') for e in errors)
    try:
        r = requests.post(GRIGORIY_URL, json={"task": f"{task}{ctx}", "user_id": 1}, timeout=120)
        if r.status_code == 200:
            d = r.json()
            return d.get("code", d.get("response", d.get("message", str(d))))
    except Exception as e:
        log(f"Ошибка сети: {e}")
    return None

def extract_code(text):
    if "```python" in text: return text.split("```python")[1].split("```")[0].strip()
    if "```" in text: return text.split("```")[1].split("```")[0].strip()
    return text

def run_code(code):
    try:
        res = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=30, cwd="/tmp")
        return res.returncode == 0, res.stdout if res.returncode == 0 else res.stderr
    except Exception as e: return False, str(e)

def log_ok(task, code):
    with open(LESSONS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n## [{datetime.now().strftime('%Y-%m-%d')}] OK: {task[:50]}\n- ✅ {code[:100]}...\n")

def log_err(task, err, att):
    d = {"errors": []}
    if ERROR_LOG_FILE.exists():
        with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f: d = json.load(f)
    d["errors"].append({"timestamp": datetime.now().isoformat(), "task": task[:100], "error": err[:500], "attempt": att})
    d["errors"] = d["errors"][-50:]
    with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=2)

def run(task, ttype):
    if not check_health():
        log("❌ Григорий не отвечает на /health"); return {"status": "fail", "error": "not running"}
    log(f"🚀 {task[:60]}...")
    lessons, errors = read_lessons(), read_errors()
    for att in range(1, 4):
        log(f"Попытка {att}/3")
        resp = call_grigoriy(task, lessons, errors)
        if not resp: continue
        if ttype == "code_execution":
            code = extract_code(resp)
            ok, out = run_code(code)
            if ok: log("✅ OK"); log_ok(task, code); return {"status": "ok", "output": out}
            log(f"❌ {out[:150]}"); log_err(task, out, att)
            task = f"Исправь:\n{out}\n\n{task}"; time.sleep(2)
        else: log("✅ OK"); return {"status": "ok", "response": resp}
    log("❌ FAIL"); return {"status": "fail"}

if __name__ == "__main__":
    if len(sys.argv) < 2: print("grigoriy_runner.py \"задача\" [text|code_execution]"); sys.exit(1)
    res = run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "text")
    print(json.dumps(res, ensure_ascii=False)); sys.exit(0 if res["status"]=="ok" else 1)
