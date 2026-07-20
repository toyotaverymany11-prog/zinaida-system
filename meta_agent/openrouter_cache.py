# -*- coding: utf-8 -*-
import os, json, time, requests, urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE_FILE = "/opt/zinaida/meta_agent/openrouter_free_cache.json"
TTL_SECONDS = 3600  # 1 час
API_URL = "https://openrouter.ai/api/v1/models"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_env():
    for path in ['/opt/zinaida/meta_agent/.env', '/root/.hermes/.env']:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('OPENROUTER_API_KEY=') and not line.startswith('#'):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None

API_KEY = _load_env()
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://zinaida.app",
    "X-Title": "Zinaida",
    "Content-Type": "application/json"
}

def _read_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if time.time() - data.get("updated_at", 0) < TTL_SECONDS:
                return data.get("models", [])
        except: pass
    return None

def _write_cache(models):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"updated_at": time.time(), "models": models}, f)
    except: pass

def fetch_free_models():
    """Динамическое получение списка :free моделей"""
    if not API_KEY:
        return []
    try:
        r = requests.get(API_URL, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            all_models = r.json().get("data", [])
            free = [m["id"] for m in all_models if m.get("id", "").endswith(":free")]
            _write_cache(free)
            return free
    except: pass
    return _read_cache() or []

def get_working_model():
    """Возвращает первую живую :free модель. При 429/404 переключается на следующую."""
    models = _read_cache()
    if not models:
        models = fetch_free_models()
    if not models:
        return None
    
    for model in models:
        try:
            r = requests.post(CHAT_URL, headers=HEADERS, json={
                "model": model,
                "messages": [{"role": "user", "content": "ok"}],
                "max_tokens": 3
            }, timeout=8)
            
            if r.status_code == 200:
                return model
            elif r.status_code in (429, 404, 402):
                # Модель мертва или лимит исчерпан → убираем из кэша и пробуем следующую
                if model in models:
                    models.remove(model)
                    _write_cache(models)
                continue
            else:
                continue
        except:
            continue
            
    # Если все модели отвалились → сбрасываем кэш и возвращаем None
    _write_cache([])
    return None

if __name__ == "__main__":
    print("🔍 ТЕСТ OPENROUTER CACHE MODULE")
    print(f"Ключ найден: {'✅' if API_KEY else '❌'}")
    print("Запрос списка :free моделей...")
    free = fetch_free_models()
    print(f"Найдено :free моделей: {len(free)}")
    if free:
        print(f"Примеры: {free[:3]}")
        print("Поиск рабочей модели...")
        working = get_working_model()
        print(f"Рабочая модель: {working or '❌ Не найдена (лимиты/блокировки)'}")
    print("✅ Тест завершён")
