import os, requests, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GRIGORIY-ROUTER] %(message)s")
logger = logging.getLogger(__name__)

def call_grigoriy(prompt: str, system: str = "", task_type: str = "code") -> str:
    env = Path("/opt/zinaida/.env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()

    chain = [
        ("Ollama", os.getenv("OLLAMA_API_KEY"), "https://api.ollama.com/v1/chat/completions", "qwen2.5-coder:7b"),
        ("GitHub", os.getenv("GITHUB_TOKEN"), "https://models.github.ai/inference/chat/completions", "gpt-4.1"),
        ("Zhipu", os.getenv("ZHIPU_API_KEY"), "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4-flash"),
    ]

    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for name, key, url, model in chain:
        if not key:
            logger.warning(f"Skipping {name}: missing key")
            continue
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": messages, "max_tokens": 3000, "temperature": 0.3}
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    logger.info(f"{name} ({model}) success")
                    return content
            logger.warning(f"{name} ({model}) failed: HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"{name} ({model}) exception: {e}")
        time.sleep(0.3)

    return "❌ Grigoriy Router: All providers failed. Check keys/network."
