import os, time, requests, urllib3, warnings
warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from gigachat_auth import get_gigachat_token
from quota_manager import check_quota, consume_quota, update_provider_state, get_provider_state
try:
    from openrouter_cache import get_working_model
except ImportError:
    get_working_model = lambda: None

def _load_env():
    for path in ['/opt/zinaida/meta_agent/.env', '/root/.hermes/.env']:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    key, sep, value = line.partition('=')
                    if sep:
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")

_load_env()

KEY_POOLS = {
    "github": [os.getenv("GITHUB_TOKEN")],
    "ollama": [os.getenv("OLLAMA_API_KEY")],
    "mistral": [os.getenv("MISTRAL_API_KEY")],
    "openrouter": [os.getenv("OPENROUTER_API_KEY")]
}

def request_complexity_score(context_size, text):
    score = 0.0
    if context_size > 1500:
        score += 0.5
    markers = ["анализ", "синтез", "план", "риски", "оцени", "сравни", "код", "скрипт", "программа"]
    for m in markers:
        if m in text.lower():
            score += 0.2
    if "[ANALYZE]" in text or "[CODE]" in text:
        score = 1.0
    return min(score, 1.0)

def get_provider(strategy, context_size=0, text=""):
    complexity = request_complexity_score(context_size, text)
    if strategy == "code":
        return {"url": "http://127.0.0.1:8003/v1/chat/completions", "headers": {}, "model": "grigoriy", "verify": True}
    chain = []
    if strategy == "analyze" or complexity > 0.7:
        chain = ["github", "mistral", "openrouter"]
    else:
        chain = ["zhipu", "gigachat", "ollama"]
    for prov in chain:
        for key in KEY_POOLS.get(prov, []):
            if not key:
                continue
            state = get_provider_state(prov, key)
            if state["status"] == "degraded" and state["cooldown_until"] > time.time():
                continue
            try:
                if prov == "github" and not check_quota("github"):
                    continue
                if prov == "gigachat":
                    token = get_gigachat_token()
                    if not token:
                        continue
                    return {"url": "https://gigachat.devices.sberbank.ru/api/v1/chat/completions", "headers": {"Authorization": f"Bearer {token}"}, "model": "GigaChat-2-Max", "verify": False}
                if prov == "openrouter":
                    model = get_working_model()
                    if not model:
                        continue
                    return {"url": "https://openrouter.ai/api/v1/chat/completions", "headers": {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://zinaida.app", "X-Title": "Zinaida"}, "model": model, "verify": True}
                if prov == "zhipu":
                    return {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "headers": {"Authorization": f"Bearer {key}"}, "model": "glm-4-flash", "verify": True}
                if prov == "mistral":
                    return {"url": "https://api.mistral.ai/v1/chat/completions", "headers": {"Authorization": f"Bearer {key}"}, "model": "mistral-small-latest", "verify": True}
                if prov == "ollama":
                    return {"url": "https://ollama.com/v1/chat/completions", "headers": {"Authorization": f"Bearer {key}"}, "model": "gemma3:4b", "verify": True}
            except Exception:
                update_provider_state(prov, key, "degraded", int(time.time()) + 1800)
                continue
    return None
