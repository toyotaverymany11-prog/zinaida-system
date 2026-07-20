#!/usr/bin/env python3
import requests, os, sys

# Читаем токен
token = None
for path in ['/root/.hermes/.env', '/opt/zinaida/config/secrets.env']:
    with open(path) as f:
        for line in f:
            if 'TG_BOT_TOKEN=' in line or 'TELEGRAM_BOT_TOKEN=' in line:
                val = line.split('=', 1)[1].strip()
                if val and val != '***':
                    token = val

if not token:
    print("❌ Token not found")
    sys.exit(1)

BASE = f'https://api.telegram.org/bot{token}'
CHAT = '6670783611'

files = [
    ('🎵 v5 xenia (женский, рекомендую)', '/opt/zinaida/livekit/zinaida-ui/test_v5_xenia.wav'),
    ('🎵 v5 baya (женский)', '/opt/zinaida/livekit/zinaida-ui/test_v5_baya.wav'),
    ('🎵 v5 kseniya (женский)', '/opt/zinaida/livekit/zinaida-ui/test_v5_kseniya.wav'),
]

for caption, path in files:
    if not os.path.exists(path):
        print(f'❌ not found: {path}')
        continue
    with open(path, 'rb') as f:
        r = requests.post(f'{BASE}/sendVoice', data={'chat_id': CHAT, 'caption': caption}, files={'voice': f}, timeout=30)
    if r.status_code == 200:
        print(f'✅ {caption.split()[1]}')
    else:
        print(f'❌ {r.status_code}: {r.text[:100]}')
        # Fallback: send as document
        with open(path, 'rb') as f:
            r = requests.post(f'{BASE}/sendDocument', data={'chat_id': CHAT, 'caption': caption}, files={'document': f}, timeout=30)
        print(f'   document: {"✅" if r.status_code == 200 else "❌"}')
