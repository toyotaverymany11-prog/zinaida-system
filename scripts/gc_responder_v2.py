#!/usr/bin/env python3
"""Group Chat Agent — отвечает на @Ольга и @Зинаида через DeepSeek.
Подключается как пользователь auth:2 (admin), чтобы ответы были видны.
"""
import socketio, json, base64, hashlib, hmac, time, requests

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"

with open("/root/.hermes-web-ui/.token") as f:
    secret = f.read().strip()

def make_jwt():
    h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps({
        "sub":"1","username":"ZinaidaSecure2026","role":"super_admin",
        "type":"access","aud":"hermes-web-ui",
        "iat":int(time.time()),"exp":int(time.time())+86400
    }).encode()).rstrip(b"=").decode()
    s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
    return h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

JWT = make_jwt()
SEEN = set()

sio = socketio.Client()

def reply(name, sender_name, msg_content):
    try:
        r = requests.post(ROUTER, json={
            "model": "deepseek-chat",
            "messages": [
                {"role":"system","content":"Ты {}. Отвечай кратко, на русском. Никогда не пиши что ты ИИ.".format(name)},
                {"role":"user","content":"От {}: {}".format(sender_name, msg_content)}
            ],
            "max_tokens": 300, "temperature": 0.7
        }, timeout=30)
        reply_text = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "Ок, поняла."
    except:
        reply_text = "Ок, поняла."
    
    print("  [{}] >> {}".format(name, reply_text[:60]), flush=True)
    sio.emit("message", {"roomId": ROOM, "content": reply_text, "id": "resp_{}".format(int(time.time()*1000))}, namespace="/group-chat")

@sio.on("*", namespace="/group-chat")
def handler(event, *args):
    if event != "message": return
    data = args[0] if args else {}
    mid = str(data.get("id","")) + str(data.get("content",""))[:20]
    if mid in SEEN: return
    SEEN.add(mid)
    sender = data.get("senderName","") or ""
    content = data.get("content","") or ""
    if sender == "Ольга" or sender == "Зинаида": return
    if not content.strip(): return
    print("  [chat] {}: {}".format(sender, content[:60]), flush=True)
    for name in ["Ольга", "Зинаида"]:
        if "@"+name in content or "@"+name.lower() in content:
            reply(name, sender, content)
            return

@sio.on("connect", namespace="/group-chat")
def connect():
    sio.emit("join", {"roomId": ROOM, "name": "Ольга", "description": "AI agent"}, namespace="/group-chat")
    print("Connected as Ольга/auth:2", flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "2", "name": "Ольга"},
    transports=["websocket", "polling"])
print("Ready. @Ольга @Зинаида", flush=True)

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": "Ольга"}, namespace="/group-chat")

try:
    sio.wait()
except:
    sio.disconnect()
