import os
import sys
import sqlite3
import re
import hashlib
import warnings

warnings.filterwarnings("ignore")

MEMORY_DIR = "/opt/zinaida/memory"
DB_PATH = f"{MEMORY_DIR}/unified_memory.db"
ENV_PATH = "/opt/zinaida/.env"

def _get_env(var, default=""):
    if not os.path.exists(ENV_PATH):
        return default
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == var:
                    return v.strip()
    return default

USE_MILVUS = _get_env("USE_MILVUS", "false").lower() == "true"

def save_fact(content, source_file, project, created_at, content_hash=None):
    if USE_MILVUS:
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("""CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, 
            source_file TEXT, project TEXT, created_at TEXT, content_hash TEXT)""")
        
        if content_hash:
            cur = conn.execute("SELECT id FROM knowledge_base WHERE content_hash=?", (content_hash,))
            if cur.fetchone():
                conn.close()
                return False
                
        conn.execute("INSERT INTO knowledge_base (content, source_file, project, created_at, content_hash) VALUES (?, ?, ?, ?, ?)",
                     (content, source_file, project, created_at, content_hash))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error in memory_router: {e}")
        return False

def search_facts(query, project="global", limit=5):
    if USE_MILVUS:
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        
        facts = []
        clean_query = re.sub(r'[^\w\s]', '', query)
        safe_query = " OR ".join([f'"{w}"' for w in clean_query.split() if len(w) > 2])
        
        if safe_query:
            try:
                cur = conn.execute("""
                    SELECT kb.content FROM knowledge_base kb
                    JOIN knowledge_fts fts ON kb.id = fts.rowid
                    WHERE knowledge_fts MATCH ? AND kb.project = ? LIMIT ?
                """, (safe_query, project, limit))
                facts = [row[0] for row in cur.fetchall()]
            except Exception:
                pass

        if not facts and project == "system":
            cur = conn.execute("SELECT content FROM knowledge_base WHERE project='system' ORDER BY id DESC LIMIT ?", (limit,))
            facts = [row[0] for row in cur.fetchall()]
            
        conn.close()
        return facts
    except Exception as e:
        print(f"DB Error in memory_router search: {e}")
        return []
