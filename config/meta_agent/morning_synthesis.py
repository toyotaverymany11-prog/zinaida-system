#!/usr/bin/env python3
"""
УТРЕННИЙ СИНТЕЗ v3.1 — ПОЛНОСТЬЮ АВТОНОМНЫЙ
Не зависит от zinaida.py. Работает напрямую через API.
Внимание: Ключи хранятся в скрипте для простоты.
Безопасно, пока доступ к серверу только у Олега.
"""
import os, json, glob, time, requests, uuid, urllib3
from datetime import datetime, timedelta

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MEMORY_DIR = "/opt/zinaida/memory/knowledge/MEMORY"
CHAT_LOGS_DIR = "/opt/zinaida/memory/chat_logs"
LOG_FILE = "/opt/zinaida/logs/synthesis.log"

# ============================================================
# API КЛЮЧИ (Хранятся здесь для автономности скрипта)
# ============================================================
KEYS = {
    "zhipu": "73c9e5dce0f64df589fdb631dfb3980c.oVgEtIBkbUgBc7XU",
    "github": "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",
    "mistral": "ITTNRjD0JrGQVUpTlKum97yoV0yAROAb",
    "gigachat": "MDE5ZDk2N2MtNTI3OS03Njc3LWJkMjktZTRlMjZjYjg4NDMxOmM4Y2RmN2EwLWM0MzMtNDBhOC04Mjk1LTMzMzVkMDM3NjIwOQ==",
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def call_api(provider, prompt, max_tokens=2000, timeout=90):
    """Прямой вызов API с обработкой ошибок"""
    if provider == "zhipu":
        return _call_openai("https://open.bigmodel.cn/api/paas/v4/chat/completions", KEYS["zhipu"], "glm-4-flash", prompt, max_tokens, timeout)
    elif provider == "github":
        return _call_openai("https://models.github.ai/inference/chat/completions", KEYS["github"], "openai/gpt-4.1-mini", prompt, max_tokens, timeout)
    elif provider == "mistral":
        return _call_openai("https://api.mistral.ai/v1/chat/completions", KEYS["mistral"], "mistral-large-latest", prompt, max_tokens, timeout)
    elif provider == "gigachat":
        return _call_gigachat(prompt, max_tokens, timeout)
    return None

def _call_openai(url, key, model, prompt, max_tokens, timeout):
    try:
        r = requests.post(url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.3},
            timeout=timeout)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        log(f"  {model}: HTTP {r.status_code}")
        return None
    except requests.exceptions.Timeout:
        log(f"  {model}: TIMEOUT")
        return None
    except Exception as e:
        log(f"  {model}: {e}")
        return None

def _call_gigachat(prompt, max_tokens, timeout):
    try:
        r = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json",
                     "RqUID": str(uuid.uuid4()), "Authorization": f"Basic {KEYS['gigachat']}"},
            data={"scope": "GIGACHAT_API_PERS"}, timeout=30, verify=False)
        if r.status_code != 200: return None
        token = r.json()["access_token"]
        r2 = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=timeout, verify=False)
        if r2.status_code == 200:
            return r2.json()["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        log(f"  GigaChat: {e}")
        return None

def safe_json(text):
    if not text: return {}
    try:
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except:
        log("️ JSON parse failed, returning empty")
        return {}

def get_logs(days=1):
    content = ""
    cutoff = datetime.now() - timedelta(days=days)
    for fpath in sorted(glob.glob(f"{CHAT_LOGS_DIR}/*.txt")):
        try:
            if datetime.fromtimestamp(os.path.getmtime(fpath)) >= cutoff:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content += f.read() + "\n"
        except: pass
    return content[-15000:] if len(content) > 15000 else content

def get_memory_context(files=["ideas.md", "incidents.md", "tools.md"]):
    """Читает последние 500 символов из файлов памяти"""
    context = {}
    for f in files:
        p = os.path.join(MEMORY_DIR, f)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    context[f] = fh.read()[-500:]
            except: pass
    return context

def is_duplicate(filepath, new_content):
    """Проверяет, нет ли уже такой записи в файле"""
    if not os.path.exists(filepath): return False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return new_content.strip() in f.read()
    except: return False

def apply_changes(mistral_result):
    approved = mistral_result.get("approved", []) if isinstance(mistral_result, dict) else []
    if not approved: return
    for item in approved:
        target = item.get("file", "ideas.md") if isinstance(item, dict) else "ideas.md"
        content = item.get("content", str(item)) if isinstance(item, dict) else str(item)
        path = os.path.join(MEMORY_DIR, target)
        os.makedirs(MEMORY_DIR, exist_ok=True)
        
        # Проверка на дубликаты
        if is_duplicate(path, content):
            log(f"⚠️ Пропущен дубль в {target}")
            continue
            
        if os.path.exists(path):
            os.system(f"cp {path} {path}.bak 2>/dev/null")
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d')}] {content}\n")
        log(f"✅ {target}")

def main():
    log("=" * 40)
    log("🌅 УТРЕННИЙ СИНТЕЗ v3.1")

    logs = get_logs()
    if len(logs) < 50:
        log("ℹ️ Мало логов, выход")
        return

    # Этап 1: Сбор
    log("🟢 Этап 1: Сбор данных (GigaChat)")
    raw = call_api("gigachat", f"Извлеки из логов ВСЁ важное: идеи, ошибки, правила, факты. Верни СТРОГО JSON с ключами ideas/errors/rules/facts.\n\n{logs}")
    raw = safe_json(raw)
    log(f"  Найдено: {sum(len(v) for v in raw.values() if isinstance(v, list))} элементов" if raw else "  Пусто")

    # Этап 2: Структура
    log("🔵 Этап 2: Структурирование (glm-4)")
    structured = call_api("zhipu", f"Структурируй данные, удали дубли. Верни JSON: {{'structured':{{...}}, 'questions':[...]}}\n\n{json.dumps(raw, ensure_ascii=False)}")
    structured = safe_json(structured)

    # Этап 3: Спор
    questions = structured.get("questions", []) if isinstance(structured, dict) else []
    if questions:
        log("🟡 Этап 3: Спор (GigaChat + glm-4)")
        answers = call_api("gigachat", f"Ответь на вопросы:\n{json.dumps(questions)}")
        final = call_api("zhipu", f"Учти ответы и выдай ФИНАЛЬНЫЙ черновик в JSON:\nОтветы: {answers}\n\nЧерновик: {json.dumps(structured, ensure_ascii=False)}")
        final = safe_json(final)
    else:
        final = structured.get("structured", {}) if isinstance(structured, dict) else {}

    # Этап 4: Валидация
    log("🔴 Этап 4: Валидация (Mistral)")
    context = get_memory_context()
    mistral = call_api("mistral", f"Утверди изменения. Контекст: {json.dumps(context)}\n\nЧерновик: {json.dumps(final, ensure_ascii=False)}\n\nВерни JSON: {{'approved':[{{'file':'...','content':'...'}}], 'rejected':[...]}}")
    mistral = safe_json(mistral)

    apply_changes(mistral)
    log("🏁 СИНТЕЗ ЗАВЕРШЁН")

if __name__ == "__main__":
    main()
