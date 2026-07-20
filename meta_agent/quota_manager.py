import sqlite3
import time

DB_PATH = "/opt/zinaida/meta_agent/quotas.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def check_quota(provider):
    conn = _get_conn()
    cur = conn.execute("SELECT used, limit_val, reset_time FROM quotas WHERE provider=?", (provider,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return True
    used, limit_val, reset_time = row
    now = time.time()
    if now > reset_time:
        conn.execute("UPDATE quotas SET used=0, reset_time=? WHERE provider=?", (now + 86400, provider))
        conn.commit()
        used = 0
    conn.close()
    return used < limit_val

def consume_quota(provider):
    conn = _get_conn()
    conn.execute("BEGIN IMMEDIATE")
    cur = conn.execute("SELECT used, limit_val, reset_time FROM quotas WHERE provider=?", (provider,))
    row = cur.fetchone()
    if row:
        used, limit_val, reset_time = row
        now = time.time()
        if now > reset_time:
            conn.execute("UPDATE quotas SET used=1, reset_time=? WHERE provider=?", (now + 86400, provider))
        else:
            conn.execute("UPDATE quotas SET used=used+1 WHERE provider=?", (provider,))
    conn.commit()
    conn.close()

def update_provider_state(provider, key, status, error_count=0):
    conn = _get_conn()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("""INSERT INTO provider_state (provider, key, status, error_count, last_error_time)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(provider, key) DO UPDATE SET status=excluded.status, error_count=excluded.error_count, last_error_time=excluded.last_error_time""",
                 (provider, key, status, error_count, int(time.time())))
    conn.commit()
    conn.close()

def get_provider_state(provider, key):
    conn = _get_conn()
    cur = conn.execute("SELECT status, cooldown_until, error_count FROM provider_state WHERE provider=? AND key=?", (provider, key))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"status": row[0], "cooldown_until": row[1], "error_count": row[2]}
    return {"status": "active", "cooldown_until": 0, "error_count": 0}
