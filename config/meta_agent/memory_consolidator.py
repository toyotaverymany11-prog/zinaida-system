#!/usr/bin/env python3
import os, sys, json, time, sqlite3, requests, re, shutil, glob, subprocess
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DB_PATH = "/opt/zinaida/memory/unified_memory.db"
GATE_FILE = "/opt/zinaida/meta_agent/.approval_gate"
PENDING_DIR = "/opt/zinaida/sandbox/pending"
CORE_URL = "http://127.0.0.1:8002/v1/chat/completions"
GRIGORIY_URL = "http://127.0.0.1:8003/v1/chat/completions"
TG_TOKEN, TG_CHAT = "", ""
ENV_PATH = "/opt/zinaida/.env"
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, _, v = line.strip().partition("=")
                if k == "TG_BOT_TOKEN": TG_TOKEN = v
                if k == "TG_CHAT_ID": TG_CHAT = v
def send_tg(text):
    if TG_TOKEN and TG_CHAT:
        try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text}, timeout=5)
        except: pass
def check_gate():
    try:
        with open(GATE_FILE, "r", encoding="utf-8") as f: return f.read().strip().lower() == "true"
    except: return False
def read_skills():
    skills = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")
        cur = conn.execute("SELECT id, content, topic, content_hash FROM knowledge_base WHERE project='autonomy_skills' ORDER BY id DESC LIMIT 100")
        for row in cur.fetchall(): skills.append({"id": row[0], "code": row[1], "topic": row[2], "hash": row[3]})
        conn.close()
    except Exception as e: print(f"DB read failed: {e}")
    return skills
def group_similar(skills):
    groups = {}
    for s in skills:
        key = re.sub(r'\W+', '_', s["topic"].lower()[:40]) if s["topic"] else "unknown"
        groups.setdefault(key, []).append(s)
    return {k: v for k, v in groups.items() if len(v) > 1}
def consolidate_group(group):
    codes = "\n---\n".join(s["code"][:1000] for s in group)
    prompt = f"ТЫ КОНСОЛИДАТОР. ОБЪЕДИНИ ДУБЛИ В ОДНО ПРАВИЛО.\n{codes}\nВЕРНИ СТРОГО JSON: {{\"consolidated_code\": \"код\", \"reason\": \"причина\"}}"
    try:
        r = requests.post(CORE_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=60)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            match = re.search(r'\{.*\}', txt, re.DOTALL)
            if match: return json.loads(match.group())
    except Exception as e: print(f"LLM failed: {e}")
    return None
def cross_validate(code):
    prompt = f"ТЫ ВАЛИДАТОР. ПРОВЕРЬ КОД.\n{code[:2000]}\nВЕРНИ СТРОГО JSON: {{\"approved\": true/false, \"reason\": \"...\"}}"
    try:
        r = requests.post(GRIGORIY_URL, json={"messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0.1}, timeout=15)
        if r.status_code == 200:
            txt = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            match = re.search(r'"approved"\s*:\s*(true|false)', txt, re.IGNORECASE)
            if match: return match.group(1).lower() == "true"
    except: pass
    return False
def apply_consolidation(new_code, group_ids):
    patch_path = os.path.join(PENDING_DIR, f"consolidation_{int(time.time())}.py")
    with open(patch_path, "w", encoding="utf-8") as f: f.write(new_code)
    res = subprocess.run(["python3", "-m", "py_compile", patch_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Compile failed: {res.stderr}")
        return False
    print("Consolidation compiled. Patch saved.")
    send_tg(f"CONSOLIDATOR: Merged {group_ids}. Patch: {patch_path}")
    return True
def main():
    print("Consolidator started.")
    skills = read_skills()
    if len(skills) < 2:
        print("Not enough skills. Exit.")
        return
    groups = group_similar(skills)
    if not groups:
        print("No duplicates. Exit.")
        return
    for topic, group in groups.items():
        print(f"Group: {topic} ({len(group)} items)")
        result = consolidate_group(group)
        if not result or "consolidated_code" not in result: continue
        if not cross_validate(result["consolidated_code"]):
            print(f"Rejected: {topic}")
            continue
        ids = [s["id"] for s in group]
        if check_gate():
            apply_consolidation(result["consolidated_code"], ids)
        else:
            pending_file = os.path.join(PENDING_DIR, f"pending_{topic}_{int(time.time())}.json")
            with open(pending_file, "w", encoding="utf-8") as f:
                json.dump({"topic": topic, "ids": ids, "code": result["consolidated_code"], "reason": result.get("reason","")}, f, ensure_ascii=False, indent=2)
            send_tg(f"CONSOLIDATOR: Pending {topic}. Gate closed.")
    print("Cycle complete.")
if __name__ == "__main__":
    main()
