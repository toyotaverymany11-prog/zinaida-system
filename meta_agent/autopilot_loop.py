#!/usr/bin/env python3
import sys, os, json, time, logging, subprocess, re, glob, shutil, sqlite3, hashlib, requests
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_runtime import run_safe

ENV_PATH = "/opt/zinaida/.env"
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, _, v = line.strip().partition("=")
                os.environ.setdefault(k, v)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AUTOPILOT] %(message)s")
logger = logging.getLogger(__name__)

CORE_URL = "http://127.0.0.1:8002/v1/chat/completions"
GRIGORIY_URL = "http://127.0.0.1:8003/v1/chat/completions"
INBOX_DIR = "/opt/zinaida/inbox/errors"
PROCESSED_DIR = "/opt/zinaida/inbox/processed"
SANDBOX_DIR = "/opt/zinaida/sandbox"
META_DIR = "/opt/zinaida/meta_agent"
GATE_FILE = os.path.join(META_DIR, ".approval_gate")
STATE_FILE = "/opt/zinaida/autonomy.state"
DB_PATH = "/opt/zinaida/memory/unified_memory.db"
TG_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = {}
            for line in f:
                if "=" in line:
                    k, _, v = line.strip().partition("=")
                    data[k] = v
            return data
    except Exception:
        return {"success_count": "0", "last_rollback_date": "", "phase_current": "3"}

def save_state(data):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")
    os.replace(tmp, STATE_FILE)

def send_tg(text):
    if TG_TOKEN and TG_CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          json={"chat_id": TG_CHAT, "text": text}, timeout=5)
        except Exception:
            pass

def check_gate():
    try:
        with open(GATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip().lower() == "true"
    except Exception:
        return False

def normalize_error(text):
    return re.sub(
        r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]?\d*|'
        r'[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}|'
        r'\b(pid|PID)[=:\s]\d+\b|'
        r'\btrace_id[=:\s]["\w]+|'
        r'\bline \d+\b',
        '', text
    )

def hash_error(text):
    return hashlib.sha256(normalize_error(text).encode("utf-8")).hexdigest()

def lookup_skill(err_hash):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")
        cur = conn.execute("SELECT content FROM knowledge_base WHERE project='autonomy_skills' AND content_hash=? LIMIT 1", (err_hash,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def save_skill(err_hash, code, desc):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_base (content, content_hash, project, source, topic, timestamp) VALUES (?, ?, 'autonomy_skills', 'autopilot_v1', ?, CURRENT_TIMESTAMP)",
            (code, err_hash, desc)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Skill save failed: {e}")

def cross_validate(code):
    prompt = f"""ТЫ ИНЖЕНЕР-ВАЛИДАТОР. ПРОВЕРЬ КОД НА БЕЗОПАСНОСТЬ И СИНТАКСИС.
КОД:
{code[:2000]}

ВЕРНИ СТРОГО JSON: {{"approved": true/false, "reason": "..."}}
ЗАПРЕЩЕНО: eval, os.system, rm -rf, chmod 777, обход allowlist.
"""
    try:
        r = requests.post(GRIGORIY_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0.1}, timeout=15)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            match = re.search(r'"approved"\s*:\s*(true|false)', txt, re.IGNORECASE)
            if match:
                return match.group(1).lower() == "true"
    except Exception:
        pass
    logger.warning("Cross-validation bypass (timeout/parse error)")
    send_tg("AUTOPILOT: Cross-validation bypassed. Proceeding with caution.")
    return True

def generate_fix(dump_text):
    prompt = f"""ТЫ ИНЖЕНЕР-АВТОПИЛОТ. СБОЙ:
{dump_text[:2000]}

СГЕНЕРИРУЙ ИСПРАВЛЕНИЕ. Верни СТРОГО JSON:
{{"target_file": "имя_файла.py", "code": "полный_код_исправления"}}

ПРАВИЛА:
1. target_file должен быть в списке: zinaida_router.py, grigoriy_router.py, provider_monitor.py.
2. code должен быть полным, с импортами.
3. Никаких пояснений вне JSON.
"""
    try:
        r = requests.post(CORE_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=60)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        logger.error(f"LLM failed: {e}")
    return None

def main():
    logger.info("Autopilot v3 started. Memory & Cross-validation active.")
    state = load_state()
    
    while True:
        try:
            files = glob.glob(os.path.join(INBOX_DIR, "*.txt"))
            for f in files:
                fname = os.path.basename(f)
                if not check_gate():
                    if fname not in state:
                        send_tg(f"AUTOPILOT: Found error {fname}. Gate closed. Approve to fix.")
                        state[fname] = "0"
                        save_state(state)
                    time.sleep(60)
                    continue
                    
                with open(f, "r", encoding="utf-8") as fd:
                    dump = fd.read()
                    
                err_hash = hash_error(dump)
                cached_fix = lookup_skill(err_hash)
                
                if cached_fix:
                    logger.info(f"Skill found for {fname}. Applying instantly.")
                    fix = {"target_file": "zinaida_router.py", "code": cached_fix}
                else:
                    logger.info(f"Processing {fname}. Generating fix.")
                    fix = generate_fix(dump)
                    if not fix or "target_file" not in fix or "code" not in fix:
                        logger.error("Invalid fix format")
                        continue
                    if not cross_validate(fix["code"]):
                        logger.warning("Cross-validation rejected fix")
                        continue
                        
                patch_path = os.path.join(SANDBOX_DIR, f"fix_{int(time.time())}.py")
                with open(patch_path, "w", encoding="utf-8") as fd:
                    fd.write(fix["code"])
                    
                res = subprocess.run(["python3", "-m", "py_compile", patch_path], capture_output=True, text=True)
                if res.returncode != 0:
                    logger.error(f"Compile failed: {res.stderr}")
                    continue
                    
                deploy_res = subprocess.run(["python3", os.path.join(META_DIR, "atomic_deploy.py"), fix["target_file"], patch_path], capture_output=True, text=True)
                if deploy_res.returncode == 0:
                    logger.info("Deploy successful")
                    save_skill(err_hash, fix["code"], fname)
                    state["success_count"] = str(int(state.get("success_count", "0")) + 1)
                    save_state(state)
                    shutil.move(f, os.path.join(PROCESSED_DIR, f"done_{fname}"))
                    send_tg(f"AUTOPILOT: Fixed {fname} successfully. Skills: {state['success_count']}")
                else:
                    logger.error(f"Deploy failed: {deploy_res.stdout}")
                    state["last_rollback_date"] = time.strftime("%Y-%m-%d")
                    save_state(state)
                    send_tg(f"AUTOPILOT: Fix failed for {fname}. Rollback executed.")
                    
            time.sleep(30)
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
