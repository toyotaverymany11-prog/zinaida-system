#!/usr/bin/env python3
"""Vision через GitHub Models. Используй: python3 /opt/zinaida/scripts/github_vision.py <image_path> [prompt]"""
import sys, json, base64, os, io, urllib.request
from PIL import Image

img_path = sys.argv[1] if len(sys.argv) > 1 else "/root/.hermes-web-ui/upload/default/c8225ca5029942b3.png"
prompt = sys.argv[2] if len(sys.argv) > 2 else "Опиши что на изображении. 2-3 предложения на русском."

# Читаем токен из secrets.env
token = None
secrets_paths = ["/opt/zinaida/config/secrets.env", "/root/.hermes/.env"]
for sp in secrets_paths:
    if os.path.exists(sp):
        with open(sp) as f:
            for line in f:
                if "GITHUB_TOKEN" in line and "=" in line:
                    token = line.split("=", 1)[1].strip().strip("'\"")
                    break
        if token:
            break

if not token:
    print("{\"error\":\"GITHUB_TOKEN не найден в secrets.env или .env\"}")
    sys.exit(1)

# Сжимаем изображение
img = Image.open(img_path)
img.thumbnail((800, 600), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, format="PNG", optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

# payload
payload = json.dumps({
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    ]}],
    "max_tokens": 300
}).encode()

req = urllib.request.Request(
    "https://models.github.ai/inference/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "Нет ответа")
        print(content)
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"Error: {e}")
