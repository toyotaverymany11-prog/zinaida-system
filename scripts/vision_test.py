#!/usr/bin/env python3
import json, base64, os, sys
from PIL import Image
import io

try:
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token:
        # try reading from secrets
        with open('/opt/zinaida/config/secrets.env') as f:
            for line in f:
                if 'GITHUB_TOKEN' in line:
                    token = line.split('=')[1].strip()
                    break
except:
    pass

if not token:
    print("NO_TOKEN")
    sys.exit(1)

import urllib.request
img = Image.open('/root/.hermes-web-ui/upload/default/c8225ca5029942b3.png')
img.thumbnail((800, 600), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, format='PNG', optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

payload = json.dumps({
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Опиши что на скриншоте. 2-3 предложения на русском."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    ]}],
    "max_tokens": 200
}).encode()

req = urllib.request.Request(
    "https://models.github.ai/inference/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        print(data.get('choices', [{}])[0].get('message', {}).get('content', 'NO_CONTENT'))
except Exception as e:
    print(f"ERROR: {e}")
