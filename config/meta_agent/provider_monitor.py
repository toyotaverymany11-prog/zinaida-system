import os, json, sqlite3, time, warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

QUOTAS_DB = "/opt/zinaida/meta_agent/quotas.db"
ENV_FILE = "/opt/zinaida/meta_agent/.env"
GIGACHAT_TOKEN_FILE = "/tmp/gigachat_token.json"
OPENROUTER_CACHE = "/opt/zinaida/meta_agent/openrouter_free_cache.json"

def load_env():
    env = {}
    if not os.path.exists(ENV_FILE):
        return env
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().replace("\r", "")
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, sep, value = line.partition("=")
            if sep:
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env

ENV = load_env()
MONITOR_TOKEN = ENV.get("MONITOR_API_TOKEN", "default_secret_token")

def check_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != MONITOR_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

def get_quotas():
    result = {}
    try:
        if not os.path.exists(QUOTAS_DB):
            return {"error": "quotas.db not found"}
        conn = sqlite3.connect(QUOTAS_DB, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        cur = conn.execute("SELECT provider_name, used_count, quota_limit, reset_time FROM quotas")
        for row in cur.fetchall():
            result[row[0]] = {
                "used": row[1],
                "limit": row[2],
                "reset_time": row[3],
                "remaining": max(0, row[2] - row[1]) if row[2] else None
            }
        conn.close()
    except Exception as e:
        result["error"] = str(e)
    return result

def get_provider_states():
    result = {}
    try:
        if not os.path.exists(QUOTAS_DB):
            return {"error": "quotas.db not found"}
        conn = sqlite3.connect(QUOTAS_DB, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        cur = conn.execute("SELECT provider_name, status, cooldown_until, error_count FROM provider_state")
        now = time.time()
        for row in cur.fetchall():
            cooldown_left = max(0, row[2] - now) if row[2] else 0
            result[row[0]] = {
                "status": row[1],
                "error_count": row[3],
                "cooldown_seconds_left": int(cooldown_left),
                "active": row[1] == "active" or cooldown_left == 0
            }
        conn.close()
    except Exception as e:
        result["error"] = str(e)
    return result

def get_gigachat_status():
    try:
        if not os.path.exists(GIGACHAT_TOKEN_FILE):
            return {"status": "no_token_file"}
        with open(GIGACHAT_TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        expires = data.get("expires_at", 0)
        now = time.time()
        return {
            "status": "active" if expires > now else "expired",
            "expires_in_seconds": int(max(0, expires - now))
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def get_openrouter_status():
    try:
        if not os.path.exists(OPENROUTER_CACHE):
            return {"status": "no_cache"}
        with open(OPENROUTER_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": "ok",
            "working_model": data.get("working_model", "unknown"),
            "free_count": data.get("free_count", 0),
            "last_updated": data.get("last_updated", 0)
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/health")
def health():
    return {"status": "ok", "service": "provider_monitor_v6.1", "port": 8004}

@app.get("/status")
def status(request: Request):
    check_auth(request)
    return {
        "timestamp": int(time.time()),
        "quotas": get_quotas(),
        "provider_states": get_provider_states(),
        "gigachat": get_gigachat_status(),
        "openrouter": get_openrouter_status()
    }

if __name__ == "__main__":
    print("STARTING PROVIDER MONITOR V6.1 ON :8004")
    uvicorn.run(app, host="0.0.0.0", port=8004)
