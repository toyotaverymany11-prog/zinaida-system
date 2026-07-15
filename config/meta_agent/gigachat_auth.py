import os, json, time, requests, urllib3, warnings
warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN_CACHE = "/tmp/gigachat_token.json"
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

def _load_env():
    for path in ['/opt/zinaida/meta_agent/.env', '/root/.hermes/.env']:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    key, sep, value = line.partition('=')
                    if sep and key.strip() in ('GIGACHAT_AUTH_KEY', 'GIGACHAT_CLIENT_ID'):
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")

_load_env()
GC_AUTH = os.getenv("GIGACHAT_AUTH_KEY")
GC_CLIENT = os.getenv("GIGACHAT_CLIENT_ID")

def get_gigachat_token():
    if not GC_AUTH or not GC_CLIENT:
        return None
    try:
        if os.path.exists(TOKEN_CACHE):
            with open(TOKEN_CACHE, "r") as f:
                data = json.load(f)
            if data.get("expires_at", 0) > time.time() + 60:
                return data["access_token"]
        r = requests.post(AUTH_URL, headers={
            "Authorization": f"Basic {GC_AUTH}",
            "RqUID": GC_CLIENT,
            "Content-Type": "application/x-www-form-urlencoded"
        }, data={"scope": "GIGACHAT_API_PERS"}, verify=False, timeout=10)
        r.raise_for_status()
        resp = r.json()
        token = resp["access_token"]
        expires = resp.get("expires_at", time.time() + 1800)
        with open(TOKEN_CACHE, "w") as f:
            json.dump({"access_token": token, "expires_at": expires}, f)
        return token
    except Exception as e:
        print(f"[gigachat_auth] Ошибка: {e}")
        return None
