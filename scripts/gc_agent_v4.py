#!/usr/bin/env python3
"""
GC Agent — подключается как super_admin (userId=1) в одном сокете,
отвечает на @Ольга и @Зинаида через DeepSeek 8003.
Пишет senderName в сообщение чтобы UI показывал имя агента.
"""
import socketio, json, requests, base64, hashlib, hmac, time, sys

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"

with open("/root/.hermes-web-ui/.token") as f:
    secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+86400}
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
jwt = h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

AGENTS = {
    "Ольга": {"system": "Ты Ольга. Отвечай кратко, по делу, на русском. Никогда не пиши что ты ИИ или тестируешь."},
    "Зинаида": {"system": "Ты Зинаида. Отвечай на русском. Никогда не пиши что ты ИИ или тестируешь."}
}

SEEN = set()
sio = socketio.Client()

def reply(name, prompt, sender, content):
    try:
        r = requests.post(ROUTER, json={
            "model": "deepseek-chat",
            "messages": [{"role":"system","content":prompt}, {"role":"user","content":"От {}: {}".format(sender, content)}],
            "max_tokens": 300, "temperature": 0.7
        }, timeout=30)
        reply = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "ок"
    except:
        reply = "Ок, поняла."
    mid = "agent_{}_{}".format(name, int(time.time()*1000))
    sio.emit("message", {
        "roomId": ROOM, "content": reply,
        "id": mid, "senderName": name,
        "timestamp": int(time.time()*1000)
    }, namespace="/group-chat")
    print("  [{}] >> {}".format(name, reply[:60]), flush=True)

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event != "message": return
    data = args[0] if args else {}
    mid = str(data.get("id","")) + str(data.get("content",""))[:20]
    if mid in SEEN: return
    SEEN.add(mid)
    sender = data.get("senderName","") or ""
    content = data.get("content","") or ""
    if sender in AGENTS: return
    if not content.strip(): return
    for name, cfg in AGENTS.items():
        if "@"+name in content or "@"+name.lower() in content:
            print("  [chat] {} -> @{}: {}".format(sender, name, content[:60]), flush=True)
            reply(name, cfg["system"], sender, content)
            return

@sio.on("connect", namespace="/group-chat")
def on_connect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026", "description": "GC Bot"}, namespace="/group-chat")
    print("Connected + joined", flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": jwt, "source": "human", "userId": "1", "name": "ZinaidaSecure2026"},
    transports=["websocket", "polling"])
print("Ready. Listening @Ольга @Зинаида", flush=True)
@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026"}, namespace="/group-chat")
sio.wait()
