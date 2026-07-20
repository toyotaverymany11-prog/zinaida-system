import os, requests, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ZINAIDA-ROUTER] %(message)s")
logger = logging.getLogger(__name__)

def call_zinaida(prompt: str, system: str = "", task_type: str = "chat") -> str:
    env = Path("/opt/zinaida/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)

    chain = [
        ("Zhipu", os.getenv("ZHIPU_API_KEY"), "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4-flash"),
        ("Mistral", os.getenv("MISTRAL_API_KEY"), "https://api.mistral.ai/v1/chat/completions", "mistral-large-latest"),
        ("GitHub", os.getenv("GITHUB_TOKEN"), "https://models.github.ai/inference/chat/completions", "gpt-4.1-mini"),
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
            payload = {"model": model, "messages": messages, "max_tokens": 2000, "temperature": 0.7}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
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

    return "❌ Zinaida Router: All providers failed. Check keys/network."
