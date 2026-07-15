import os, json, requests, time, threading
from datetime import datetime, timezone

KEYS = {
    "zhipu": os.environ.get("ZHIPU_API_KEY", "73c9e5dce0f64df589fdb631dfb3980c.oVgEtIBkbUgBc7XU"),
    "github": os.environ.get("GITHUB_TOKEN", "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"),
    "openrouter": os.environ.get("OPENROUTER_API_KEY", "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"),
    "gigachat_auth": os.environ.get("GIGACHAT_AUTH_KEY", "MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZlYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ=="),
    "gigachat_rquid": os.environ.get("GIGACHAT_RQUID", "019d967c-5279-7677-bd29-e4e26eb88431"),
    "ollama": os.environ.get("OLLAMA_KEY", "4cd339f81a8949ca859b74add25644cc.0mpl6iHetsyydTA6vdkXa6jq")
}

_cache = {
    "openrouter_free_models": [],
    "openrouter_cache_time": 0,
    "gigachat_token": None,
    "gigachat_token_expiry": 0,
    "usage_log": []
}
_lock = threading.Lock()
USAGE_LOG_PATH = "/opt/zinaida/logs/provider_usage.json"

def _log_usage(provider, model, status, error=None):
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "provider": provider, "model": model, "status": status, "error": error}
    with _lock:
        _cache["usage_log"].append(entry)
        try:
            with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(_cache["usage_log"][-100:], f, ensure_ascii=False, indent=2)
        except Exception: pass

def call_zhipu(messages, model="glm-4-flash"):
    try:
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={"Authorization": f"Bearer {KEYS['zhipu']}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.7}, timeout=15)
        if resp.status_code == 200: return resp.json()
        _log_usage("zhipu", model, "fail", f"HTTP {resp.status_code}")
    except Exception as e: _log_usage("zhipu", model, "error", str(e))
    return None

def call_github(messages, model="gpt-4.1-mini"):
    try:
        resp = requests.post("https://models.inference.ai.azure.com/chat/completions",
            headers={"Authorization": f"Bearer {KEYS['github']}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.7}, timeout=20)
        if resp.status_code == 200: return resp.json()
        _log_usage("github", model, "fail", f"HTTP {resp.status_code}")
    except Exception as e: _log_usage("github", model, "error", str(e))
    return None

def _refresh_openrouter_models():
    if time.time() - _cache["openrouter_cache_time"] < 3600: return
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {KEYS['openrouter']}", "HTTP-Referer": "https://zinaida.app", "X-Title": "Zinaida"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            _cache["openrouter_free_models"] = [m["id"] for m in data if m.get("id", "").endswith(":free")]
            _cache["openrouter_cache_time"] = time.time()
    except Exception: pass

def call_openrouter(messages, model=None):
    _refresh_openrouter_models()
    models_to_try = [model] if model else _cache["openrouter_free_models"][:3] or ["meta-llama/llama-3-8b-instruct:free"]
    for m in models_to_try:
        try:
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {KEYS['openrouter']}", "HTTP-Referer": "https://zinaida.app", "X-Title": "Zinaida", "Content-Type": "application/json"},
                json={"model": m, "messages": messages, "temperature": 0.7}, timeout=25)
            if resp.status_code == 200: return resp.json()
            _log_usage("openrouter", m, "fail", f"HTTP {resp.status_code}")
        except Exception as e: _log_usage("openrouter", m, "error", str(e))
    return None

def _refresh_gigachat_token():
    if time.time() < _cache["gigachat_token_expiry"]: return _cache["gigachat_token"]
    try:
        resp = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {KEYS['gigachat_auth']}", "RqUID": KEYS["gigachat_rquid"], "Content-Type": "application/x-www-form-urlencoded"},
            data="scope=GIGACHAT_API_PERS", verify=False, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            _cache["gigachat_token"] = data["access_token"]
            exp = data.get("expires_at", 0)
            _cache["gigachat_token_expiry"] = (exp / 1000) if exp > 1e12 else time.time() + 1800
            return _cache["gigachat_token"]
    except Exception: pass
    return None

def call_gigachat(messages, model="GigaChat-2-Max"):
    token = _refresh_gigachat_token()
    if not token: return None
    try:
        resp = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 1000, "temperature": 0.7}, verify=False, timeout=20)
        if resp.status_code == 200: return resp.json()
        _log_usage("gigachat", model, "fail", f"HTTP {resp.status_code}")
    except Exception as e: _log_usage("gigachat", model, "error", str(e))
    return None

def call_ollama(messages, model="gemma3:4b"):
    try:
        resp = requests.post("https://ollama.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {KEYS['ollama']}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.7}, timeout=25)
        if resp.status_code == 200: return resp.json()
        _log_usage("ollama", model, "fail", f"HTTP {resp.status_code}")
    except Exception as e: _log_usage("ollama", model, "error", str(e))
    return None

def route_request(messages, task_type="chat"):
    chains = {
        "chat": [("zhipu", "glm-4-flash"), ("openrouter", None), ("ollama", "gemma3:4b")],
        "code": [("github", "gpt-4.1-mini"), ("openrouter", None)],
        "analysis": [("github", "gpt-4.1-mini"), ("openrouter", None), ("zhipu", "glm-4-flash")],
        "creative": [("gigachat", "GigaChat-2-Max"), ("openrouter", None), ("zhipu", "glm-4-flash")]
    }
    for provider, model in chains.get(task_type, chains["chat"]):
        try:
            if provider == "zhipu": res = call_zhipu(messages, model)
            elif provider == "github": res = call_github(messages, model)
            elif provider == "openrouter": res = call_openrouter(messages, model)
            elif provider == "gigachat": res = call_gigachat(messages, model)
            elif provider == "ollama": res = call_ollama(messages, model)
            else: continue
            if res and "choices" in res:
                _log_usage(provider, model or "auto", "success")
                return res
        except Exception: continue
    _log_usage("all", "none", "fallback_exhausted")
    return {"error": "All providers failed", "choices": []}

def get_provider_health():
    return {
        "cache": {
            "openrouter_free_models_count": len(_cache.get("openrouter_free_models", [])),
            "openrouter_cache_age_sec": int(time.time() - _cache.get("openrouter_cache_time", 0)),
            "gigachat_token_valid": time.time() < _cache.get("gigachat_token_expiry", 0)
        },
        "usage_log_size": len(_cache.get("usage_log", [])),
        "last_5_entries": _cache.get("usage_log", [])[-5:]
    }
