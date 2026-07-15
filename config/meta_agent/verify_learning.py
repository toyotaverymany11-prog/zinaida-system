import os
import sys
import json
import sqlite3
import requests
import time
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

DB_PATH = "/opt/zinaida/memory/unified_memory.db"
ROUTER_URL = "http://127.0.0.1:8002/v1/chat/completions"
LOG_PATH = "/opt/zinaida/logs/verification_events.jsonl"

def log_event(event):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def get_recent_facts(limit=5):
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        cur = conn.execute("SELECT id, content, project FROM knowledge_base ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "content": r[1], "project": r[2]} for r in rows]
    except Exception as e:
        print(f"DB Error: {e}")
        return []

def verify_fact(fact):
    prompt = f"Подтверди, что тебе известен следующий факт из базы знаний. Ответь кратко: да или нет. Факт: {fact['content'][:200]}"
    try:
        resp = requests.post(ROUTER_URL, json={
            "messages": [{"role": "user", "content": prompt}],
            "stream": False, "temperature": 0.1
        }, timeout=10)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].lower()
        status = "PASS" if "да" in content or "известен" in content or "подтверждаю" in content else "FAIL"
        return status
    except Exception as e:
        return f"ERROR: {e}"

def main():
    facts = get_recent_facts(5)
    if not facts:
        print("Нет фактов для верификации.")
        return
    for fact in facts:
        status = verify_fact(fact)
        event = {
            "timestamp": datetime.now().isoformat(),
            "fact_id": fact["id"],
            "project": fact["project"],
            "status": status
        }
        log_event(event)
        print(f"Fact {fact['id']}: {status}")
        time.sleep(1)

if __name__ == "__main__":
    main()
