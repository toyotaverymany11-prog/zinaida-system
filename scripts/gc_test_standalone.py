#!/usr/bin/env python3
"""Одиночный тест подключения к Group Chat"""
import socketio, json, base64, hashlib, hmac, time

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"

with open("/root/.hermes-web-ui/.token") as f:
    secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+3600}
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
jwt = h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

sio = socketio.Client()
logged = set()

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event == "message":
        data = args[0] if args else {}
        mid = str(data.get("id","")) + str(data.get("_id","")) + str(data.get("content",""))[:20]
        if mid in logged: return
        logged.add(mid)
        sender = data.get("senderName","?")
        content = data.get("content","") or ""
        print("  [{}] {}".format(sender, content[:120]), flush=True)

@sio.on("connect", namespace="/group-chat")
def on_connect():
    print("✓ Connected to /group-chat", flush=True)
    sio.emit("join", {"roomId": ROOM, "name": "Zinaida"}, namespace="/group-chat")
    print("✓ Joined room. Waiting for messages...", flush=True)
    time.sleep(2)
    print(">>> Sending test @Зинаида...", flush=True)
    sio.emit("message", {"roomId": ROOM, "content": "@Зинаида тест, ответь коротко"}, namespace="/group-chat")
    print(">>> Sent!", flush=True)

@sio.on("connect_error", namespace="/group-chat")
def on_err(e):
    print("Error: {}".format(e), flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": jwt, "source": "human", "userId": "zina_test"},
    transports=["websocket"])

time.sleep(15)
print("\n--- Всего событий получено: {} ---".format(len(logged)))
sio.disconnect()
