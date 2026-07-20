#!/usr/bin/env python3
"""Анализ консилиума через GitHub Models. Читает токен из .env"""
import json, urllib.request, os

# Read token from .env
token = ""
for path in ["/root/.hermes/.env", "/opt/zinaida/config/secrets.env"]:
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if "GITHUB_TOKEN" in line and "=" in line:
                    val = line.split("=", 1)[1].strip().strip("'\"")
                    if len(val) > 10:
                        token = val
                        break
    if token:
        break

if not token:
    print("NO_TOKEN")
    exit(1)

payload = json.dumps({
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "Ты аналитик контент-завода Зинаида. Проект: генерация контента в нише психологии отношений, картинки через Replicate, интерфейс Hermes Studio. Выбери 3 самых важных находки из данных ниже. Коротко: почему важно и что делать."},
        {"role": "user", "content": "REPLICATE: 1) Cloudflare купил Replicate в 2026 году. 2) Replicate Flux MCP Server — новый MCP-сервер. 3) Новые цены Replicate 2026. HERMES STUDIO: 1) Вышел v0.6.27 сегодня. 2) Multiple Agents в одном group-chat — issue #10965. 3) Agent teams в Telegram уже протестировали."}
    ],
    "max_tokens": 400
}).encode()

req = urllib.request.Request(
    "https://models.github.ai/inference/chat/completions",
    data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "NO_CONTENT")
        print(content)
except Exception as e:
    print(f"ERROR: {e}")