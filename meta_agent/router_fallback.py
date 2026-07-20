import os, requests, time
from pathlib import Path

def call_with_fallback(prompt: str, system: str = "", task_type: str = "chat"):
    env = Path("/opt/zinaida/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k,v = line.strip().split("=",1)
                os.environ.setdefault(k,v)
    
    if task_type == "code":
        chain = [
            ("OpenRouter", os.getenv("OPENROUTER_KEY"), "https://openrouter.ai/api/v1/chat/completions", "poolside/laguna-m.1:free"),
            ("GitHub", os.getenv("GITHUB_TOKEN"), "https://models.github.ai/inference/chat/completions", "openai/gpt-4.1"),
        ]
    else:
        chain = [
            ("Zhipu", os.getenv("ZHIPU_API_KEY"), "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4-flash"),
            ("GitHub", os.getenv("GITHUB_TOKEN"), "https://models.github.ai/inference/chat/completions", "openai/gpt-4.1-mini"),
            ("GigaChat", os.getenv("GIGACHAT_CLIENT_ID"), "https://gigachat.devices.sberbank.ru/api/v1/chat/completions", "GigaChat"),
        ]
    
    for name, key, url, model in chain:
        if not key: continue
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            if "openrouter" in url: headers.update({"HTTP-Referer":"http://localhost","X-Title":"Zinaida"})
            payload = {"model": model, "messages": [{"role":"system","content":system}, {"role":"user","content":prompt}], "max_tokens": 1500}
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"⚠️ {name} failed: {e}")
            time.sleep(0.5)
            continue
    return "❌ Все модели недоступны"
