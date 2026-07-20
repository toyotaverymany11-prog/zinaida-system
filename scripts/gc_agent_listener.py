#!/usr/bin/env python3
"""
Group Chat Agent Listener for @Оля
Подключается к комнате Group Chat через Socket.IO, слушает @упоминания,
и отвечает простыми сообщениями через WebSocket.
"""
import socketio
import json
import base64
import hashlib
import hmac
import time
import urllib.request
import urllib.error
import sys

WEB_UI_URL = "http://127.0.0.1:8648"
ROOM_ID = "mrj9nkx8nln7lx"

def get_jwt():
    with open('/root/.hermes-web-ui/.token') as f:
        secret = f.read().strip()
    h = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
    p = base64.urlsafe_b64encode(json.dumps({
        'sub':'1','username':'ZinaidaSecure2026','role':'super_admin',
        'type':'access','aud':'hermes-web-ui',
        'iat':int(time.time()),'exp':int(time.time())+3600
    }).encode()).rstrip(b'=').decode()
    s = hmac.new(secret.encode(), f'{h}.{p}'.encode(), hashlib.sha256).digest()
    return f'{h}.{p}.{base64.urlsafe_b64encode(s).rstrip(b"=").decode()}'

def send_message(sio, content):
    """Send a message through Socket.IO"""
    sio.emit('message', {
        'roomId': ROOM_ID,
        'content': content,
    }, namespace='/group-chat')
    print(f"  >> Sent: {content[:80]}")

def get_avatar_url():
    """Generate URL for avatar"""
    return f"{WEB_UI_URL}/api/auth/avatar"

sio = socketio.Client()
jwt = get_jwt()
last_msg_id = ""

# Handler for ALL events from /group-chat namespace
@sio.on('*', namespace='/group-chat')
def catch_all(event, *args):
    global last_msg_id
    data = args[0] if args else {}
    
    if event == 'message':
        msg_id = data.get('id', '')
        content = data.get('content', '')
        sender_id = data.get('senderId', '')
        sender_name = data.get('senderName', '')
        
        # Skip own messages
        if sender_id == 'auth:1':
            return
        
        # Skip if already responded to this message
        if msg_id == last_msg_id:
            return
        
        # Check for @Оля mentions
        mentions = ['@Оля', '@оля', '@olya']
        if any(m in content for m in mentions):
            last_msg_id = msg_id
            print(f"\n  << @Оля detected from {sender_name}: {content[:80]}")
            
            # Simple response
            response = f"@{sender_name}, привет! Вижу твоё сообщение: «{content[:50]}». Поняла, работаю."
            send_message(sio, response)

@sio.on('connect', namespace='/group-chat')
def gc_connect():
    print("✓ Connected to /group-chat!")
    sio.emit('join', {'roomId': ROOM_ID}, namespace='/group-chat')
    print(f"✓ Joined room {ROOM_ID}")
    print(f"✓ Listening for @Оля...")

@sio.on('connect_error', namespace='/group-chat')
def gc_error(data):
    print(f"✗ Connection error: {data}")

print("Starting Group Chat Agent Listener...")
print(f"Room: {ROOM_ID}")
print(f"Token validated: {len(jwt)} chars")
print()

sio.connect(WEB_UI_URL, namespaces=['/group-chat'], auth={'token': jwt})
print()

try:
    sio.wait()
except KeyboardInterrupt:
    sio.disconnect()
