#!/usr/bin/env python3
import os
import sys
import sqlite3
import subprocess
import hashlib
import fcntl
import argparse
import json
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

MEMORY_DIR = Path("/opt/zinaida/memory")
PROJECT_DIR = Path("/opt/zinaida/inbox/PROJECTS/Otnoshenya")
YADRO_DIR = Path("/opt/zinaida/yadro")
SCRIPTS_DIR = Path("/opt/zinaida/scripts")
SLEPOK_PATH = MEMORY_DIR / "SYSTEM_SNAPSHOT.md"
GIVOY_LINK = MEMORY_DIR / "givoy_slepok.md"
AGENT_CTX_PATH = MEMORY_DIR / "AGENT_CONTEXT.json"
TMP_PATH = SLEPOK_PATH.with_suffix(".md.tmp")
LOCK_PATH = Path("/tmp/givoy_slepok.lock")

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "ERROR"

def db_count(path, table):
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        val = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        conn.close()
        return str(val)
    except Exception:
        return "MISSING"

def get_hash(fp):
    try:
        with open(fp, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return "NOT_FOUND"

def check_inject(path, pattern):
    try:
        if not Path(path).exists():
            return "НЕТ"
        res = run("grep -c '" + pattern + "' '" + str(path) + "'")
        return "ДА" if res.isdigit() and int(res) > 0 else "НЕТ"
    except Exception:
        return "НЕТ"

def check_rag_clean():
    try:
        conn = sqlite3.connect(str(MEMORY_DIR / "smm_rag.db"))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        dirty = conn.execute("SELECT COUNT(*) FROM smm_knowledge_fts WHERE content LIKE '%Важно понимать%' OR content LIKE '%Таким образом%'").fetchone()[0]
        conn.close()
        return "ДА (0 dirty)" if dirty == 0 else "НЕТ (" + str(dirty) + " dirty)"
    except Exception:
        return "ERROR"

def build_auto():
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("# SYSTEM SNAPSHOT: АВТОМАТИЧЕСКИЙ [" + ts + "]")
    L.append("")
    L.append("## ЯДРО И СЕРВИСЫ")
    L.append("ira-bot: " + run("systemctl is-active ira-bot.service"))
    L.append("caddy: " + run("systemctl is-active caddy.service"))
    L.append("Порты: " + run("ss -tlnp | grep -E ':(8002|8003|443|80) ' | wc -l") + " активных")
    L.append("")
    L.append("## БАЗЫ ДАННЫХ")
    L.append("phases.db: " + db_count(PROJECT_DIR / "phases.db", "phases") + " записей")
    L.append("smm_rag.db: " + db_count(MEMORY_DIR / "smm_rag.db", "smm_knowledge_fts") + " чанков")
    L.append("analytics.db (experiment_log): " + db_count(MEMORY_DIR / "analytics.db", "experiment_log"))
    L.append("analytics.db (post_metrics): " + db_count(MEMORY_DIR / "analytics.db", "post_metrics"))
    L.append("content_rotation.db: " + db_count(MEMORY_DIR / "content_rotation.db", "content_rotation"))
    L.append("")
    L.append("## ХЕШИ ЯДРА")
    L.append("pulse.py: " + get_hash(YADRO_DIR / "orchestrator/pulse.py"))
    L.append("verifier_v3.py: " + get_hash(YADRO_DIR / "orchestrator/verifier_v3.py"))
    L.append("publisher.py: " + get_hash(YADRO_DIR / "orchestrator/publisher.py"))
    L.append("curator_job.py: " + get_hash(YADRO_DIR / "orchestrator/curator_job.py"))
    L.append("")
    L.append("## ИНЪЕКЦИИ И ФИКСЫ")
    L.append("JSON-парсер (_safe_json_loads): " + check_inject(YADRO_DIR / "orchestrator/pulse.py", "_safe_json_loads"))
    L.append("Critic stdout JSON: " + check_inject(SCRIPTS_DIR / "internal_critic.py", "json.dumps"))
    L.append("RAG detox: " + check_rag_clean())
    L.append("SOUL.md: " + ("ДА" if Path("/root/.hermes/profiles/zinaida/SOUL.md").exists() else "НЕТ"))
    L.append("Calibrate retry: " + check_inject(SCRIPTS_DIR / "calibrate_single.py", "range(2)"))
    L.append("")
    L.append("## ATTACK LAYER")
    L.append("CTA: " + run("ls -1 " + str(PROJECT_DIR / "cta_library") + "/*.md 2>/dev/null | wc -l") + " файлов")
    L.append("Hooks: " + run("ls -1 " + str(PROJECT_DIR / "hooks/templates") + "/*.md 2>/dev/null | wc -l") + " файлов")
    L.append("Stats: " + run("ls -1 " + str(PROJECT_DIR / "stats/mechanics") + "/*.md 2>/dev/null | wc -l") + " файлов")
    L.append("")
    L.append("---")
    L.append("Сгенерировано: " + ts + " | Режим: --auto")
    return "\n".join(L)

def build_agent_context():
    data = {
        "snapshot_ts": datetime.utcnow().isoformat(),
        "paths": {
            "memory": str(MEMORY_DIR),
            "project": str(PROJECT_DIR),
            "yadro": str(YADRO_DIR)
        },
        "hashes": {
            "pulse": get_hash(YADRO_DIR / "orchestrator/pulse.py"),
            "verifier": get_hash(YADRO_DIR / "orchestrator/verifier_v3.py"),
            "publisher": get_hash(YADRO_DIR / "orchestrator/publisher.py")
        },
        "db_counts": {
            "phases": int(db_count(PROJECT_DIR / "phases.db", "phases") or 0),
            "rag_chunks": int(db_count(MEMORY_DIR / "smm_rag.db", "smm_knowledge_fts") or 0),
            "experiments": int(db_count(MEMORY_DIR / "analytics.db", "experiment_log") or 0),
            "metrics": int(db_count(MEMORY_DIR / "analytics.db", "post_metrics") or 0)
        },
        "flags": {
            "safe_json": check_inject(YADRO_DIR / "orchestrator/pulse.py", "_safe_json_loads") == "ДА",
            "critic_stdout": check_inject(SCRIPTS_DIR / "internal_critic.py", "json.dumps") == "ДА",
            "soul_md": Path("/root/.hermes/profiles/zinaida/SOUL.md").exists(),
            "rag_clean": check_rag_clean().startswith("ДА")
        },
        "limits": {
            "token_budget": 8000,
            "tg_chars": 4096,
            "ig_chars": 2200,
            "vk_chars": 1500
        }
    }
    return json.dumps(data, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "compact", "auto"], default="auto")
    args = parser.parse_args()
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Lock busy. Exit.")
        sys.exit(0)
    try:
        content = build_auto()
        with open(TMP_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(TMP_PATH, SLEPOK_PATH)
        os.chmod(SLEPOK_PATH, 0o644)
        if GIVOY_LINK.exists() or GIVOY_LINK.is_symlink():
            GIVOY_LINK.unlink()
        os.symlink(SLEPOK_PATH, GIVOY_LINK)
        ctx = build_agent_context()
        with open(AGENT_CTX_PATH, "w", encoding="utf-8") as f:
            f.write(ctx)
        print("✅ Слепок обновлён (" + args.mode + "): " + str(SLEPOK_PATH))
        print("✅ Контекст агента: " + str(AGENT_CTX_PATH))
    except Exception as e:
        print("🔴 Ошибка: " + str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

if __name__ == "__main__":
    main()
