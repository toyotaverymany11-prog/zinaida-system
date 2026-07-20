#!/usr/bin/env python3
import requests, os

# Читаем токен из .env
env_path = '/root/.hermes/.env'
token = None
with open(env_path) as f:
    for line in f:
        if 'TG_BOT_TOKEN=' in line:
            token = line.split('=', 1)[1].strip()
            break

if not token:
    print("Token not found")
    exit(1)

BASE = f'https://api.telegram.org/bot{token}'
CHAT = '6670783611'

# Проверяем бота
r = requests.get(f'{BASE}/getMe', timeout=5)
print(f"Bot: {r.json()['result']['username']}")

files = [
    ('kseniya (женский)', '/opt/zinaida/livekit/zinaida-ui/test_silero_kseniya.ogg'),
    ('xenia (женский)', '/opt/zinaida/livekit/zinaida-ui/test_silero_xenia.ogg'),
]

for label, path in files:
    with open(path, 'rb') as f:
        resp = requests.post(f'{BASE}/sendVoice', data={'chat_id': CHAT, 'caption': label}, files={'voice': f}, timeout=10)
    if resp.status_code == 200:
        print(f'✅ {label}')
    else:
        print(f'❌ {resp.status_code} {resp.text[:100]}')
