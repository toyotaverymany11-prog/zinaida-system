#!/usr/bin/env python3
"""Тест GC: отправляет @Ольга и ждёт ответ"""
import socketio, json, base64, hashlib, hmac, time, sys

WEB_UI_URL = "http://127.0.0.1:8648"
ROOM_ID = "mrj9nkx8nln7lx"

with open("/root/.hermes-web-ui/.token") as f: secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
p_data = {"sub":"1","username":"tester","role":"admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+60}
p = base64.urlsafe_b64encode(json.dumps(p_data).encode()).rstrip(b"=").decode()
sig = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
jwt = h+"."+p+"."+base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

sio = socketio.Client()
responses = []

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event == "message":
        data = args[0] if args else {}
        print(f"  [{data.get('senderName','?')}] {data.get('content','')[:120]}")
        responses.append(data)

@sio.on("connect", namespace="/group-chat")
def on_connect():
    print("✓ Connected!")
    sio.emit("join", {"roomId": ROOM_ID, "name": "tester"}, namespace="/group-chat")
    time.sleep(1)
    msg = "@Ольга привет, напиши короткий ответ одним предложением"
    sio.emit("message", {"roomId": ROOM_ID, "content": msg, "id": f"t{int(time.time())}"}, namespace="/group-chat")
    print(f"\n--- Отправил: {msg} ---")

@sio.on("connect_error", namespace="/group-chat")
def on_err(e): print(f"Error: {e}")

sio.connect(WEB_UI_URL, namespaces=["/group-chat"], auth={"token": jwt}, transports=["websocket"])

time.sleep(15)
print(f"\nВсего сообщений: {len(responses)}")
for r in responses:
    s = r.get('senderName','?')
    c = r.get('content','')[:120]
    print(f"  [{s}] {c}")
sio.disconnect()
