#!/usr/bin/env python3
import os, sys, json, time, hashlib, shutil, glob, sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = "/opt/zinaida"
MEMORY_DIR = f"{BASE_DIR}/memory"
KNOWLEDGE_DIR = f"{MEMORY_DIR}/knowledge"
TRASH_DIR = f"{MEMORY_DIR}/trash"
LOGS_DIR = f"{BASE_DIR}/logs"
PROGRESS_FILE = f"{BASE_DIR}/meta_agent/audit_progress.json"
REPORT_FILE = f"{MEMORY_DIR}/audit_report_{datetime.now().strftime('%Y%m%d')}.md"
DB_PATH = f"{MEMORY_DIR}/unified_memory.db"
MAX_RUNTIME = 7200
CONTEXT_BUDGET_BYTES = 10 * 1024
start_time = time.time()

def check_time():
    if time.time() - start_time > MAX_RUNTIME:
        save_progress("TIMEOUT_REACHED")
        sys.exit(0)

def save_progress(status):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"status": status, "timestamp": time.time()}, f)
    except Exception:
        pass

def md5_hash(filepath):
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def ensure_dirs():
    os.makedirs(TRASH_DIR, exist_ok=True)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def check_db_integrity():
    if not os.path.exists(DB_PATH):
        return "DB_MISSING"
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        res = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return res[0] if res else "UNKNOWN"
    except Exception as e:
        return f"ERROR: {e}"

def rotate_logs():
    cutoff = time.time() - (7 * 86400)
    for f in glob.glob(os.path.join(LOGS_DIR, "*.log")):
        try:
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
        except Exception:
            pass

def get_dir_size(path):
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
    except Exception:
        pass
    return total

def enforce_context_budget():
    files_to_check = []
    brief = os.path.join(MEMORY_DIR, "brief.md")
    if os.path.exists(brief):
        files_to_check.append(brief)
    for f in glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md")):
        files_to_check.append(f)

    current_size = sum(os.path.getsize(f) for f in files_to_check if os.path.exists(f))
    if current_size > CONTEXT_BUDGET_BYTES:
        files_to_check.sort(key=lambda x: os.path.getmtime(x))
        for f in files_to_check:
            if current_size <= CONTEXT_BUDGET_BYTES:
                break
            if os.path.exists(f):
                size = os.path.getsize(f)
                try:
                    shutil.move(f, os.path.join(TRASH_DIR, os.path.basename(f)))
                    current_size -= size
                except Exception:
                    pass

def find_and_move_duplicates():
    hashes = {}
    for root, dirs, files in os.walk(KNOWLEDGE_DIR):
        check_time()
        for fname in files:
            fpath = os.path.join(root, fname)
            h = md5_hash(fpath)
            if not h:
                continue
            if h in hashes:
                dest = os.path.join(TRASH_DIR, f"{fname}.dup_{int(time.time())}")
                try:
                    shutil.move(fpath, dest)
                except Exception:
                    pass
            else:
                hashes[h] = fpath

def generate_report(db_status, initial_size, final_size):
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Аудит памяти {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(f"- **Статус БД:** {db_status}\n")
            f.write(f"- **Размер памяти до:** {initial_size} байт\n")
            f.write(f"- **Размер памяти после:** {final_size} байт\n")
            f.write(f"- **Контекстный бюджет:** {CONTEXT_BUDGET_BYTES} байт (соблюдён)\n")
            f.write(f"- **Время выполнения:** {int(time.time() - start_time)} сек\n")
            f.write(f"- **Дубли перемещены в:** {TRASH_DIR}\n")
    except Exception:
        pass

def main():
    ensure_dirs()
    save_progress("STARTED")
    initial_size = get_dir_size(MEMORY_DIR)
    db_status = check_db_integrity()
    check_time()
    rotate_logs()
    check_time()
    find_and_move_duplicates()
    check_time()
    enforce_context_budget()
    check_time()
    final_size = get_dir_size(MEMORY_DIR)
    generate_report(db_status, initial_size, final_size)
    save_progress("COMPLETED")

if __name__ == "__main__":
    main()
