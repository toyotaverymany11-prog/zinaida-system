#!/usr/bin/env python3
"""Авторемонт state.db — проверка целостности, FTS5, восстановление схемы."""
import sqlite3, os, sys, time, shutil, logging

DB_PATH = "/root/.hermes/state.db"
LOG_PATH = "/opt/zinaida/logs/repair_db.log"

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s [REPAIR] %(message)s")
log = logging.getLogger("repair_db")

def check_integrity(conn):
    result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    return result == "ok"

def check_fts5(conn):
    """Проверяем что FTS5 таблицы существуют и работают."""
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        has_fts = "messages_fts" in tables
        if has_fts:
            # Пробуем простой запрос
            conn.execute("SELECT * FROM messages_fts LIMIT 1")
        return has_fts
    except Exception as e:
        log.warning("FTS5 check failed: %s", e)
        return False

def rebuild_fts(conn):
    """Перестроить FTS5 индекс."""
    try:
        conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        conn.commit()
        log.info("FTS5 index rebuilt successfully")
        return True
    except Exception as e:
        log.warning("FTS5 rebuild failed: %s", e)
        return False

def vacuum_db(conn):
    try:
        conn.execute("VACUUM")
        log.info("VACUUM completed")
    except Exception as e:
        log.warning("VACUUM failed: %s", e)

def main():
    if not os.path.exists(DB_PATH):
        log.error("Database not found: %s", DB_PATH)
        return 1
    
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        
        # 1. Integrity check
        if not check_integrity(conn):
            log.error("INTEGRITY FAILED! Creating backup and attempting repair...")
            backup = DB_PATH + f".backup.{int(time.time())}"
            shutil.copy2(DB_PATH, backup)
            log.info("Backup created: %s", backup)
            # Пробуем VACUUM для восстановления
            vacuum_db(conn)
            if not check_integrity(conn):
                log.error("STILL CORRUPTED after VACUUM. Manual intervention needed.")
                conn.close()
                return 2
        else:
            log.info("Integrity check: OK")
        
        # 2. FTS5 check
        if not check_fts5(conn):
            log.warning("FTS5 missing or broken, rebuilding...")
            rebuild_fts(conn)
        else:
            log.info("FTS5 index: OK")
        
        # 3. Периодический VACUUM (раз в неделю)
        stat = os.stat(DB_PATH)
        size_mb = stat.st_size / (1024 * 1024)
        if size_mb > 100:  # Если больше 100 МБ
            log.info("DB size %.1f MB, running VACUUM...", size_mb)
            vacuum_db(conn)
        
        conn.close()
        log.info("Repair complete. DB size: %.1f MB", os.path.getsize(DB_PATH) / (1024*1024))
        return 0
    except Exception as e:
        log.error("Repair script failed: %s", e)
        return 3

if __name__ == "__main__":
    sys.exit(main())
