#!/usr/bin/env python3
"""Тест: подключаюсь, джойню, отправляю @Зинаида, смотрю что приходит"""
import socketio, json, base64, hashlib, hmac, time, sys

with open("/root/.hermes-web-ui/.token") as f: secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+3600}
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
JWT = h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

sio = socketio.Client()
msgs = []

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event == "message":
        data = args[0] if args else {}
        msgs.append(data)
        print("MSG: [{}] {}".format(data.get("senderName","?"), data.get("content","")[:80]), flush=True)
    elif event == "join_error" or event == "error":
        print("EVENT {}: {}".format(event, args), flush=True)

@sio.on("connect", namespace="/group-chat")
def on_connect():
    print("Connected. Sending join...", flush=True)
    # join с callback
    sio.emit("join", {"roomId": "mrj9nkx8nln7lx", "name": "tester"}, namespace="/group-chat",
        callback=lambda d: print("Join callback: {}".format(d), flush=True))
    
    time.sleep(2)
    print("Sending message...", flush=True)
    # отправка с callback
    sio.emit("message", {"roomId": "mrj9nkx8nln7lx", "content": "@Ольга тест", "id": "t1"}, namespace="/group-chat",
        callback=lambda d: print("Msg callback: {}".format(d), flush=True))

sio.connect("http://127.0.0.1:8648", namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "tester", "name": "tester"},
    transports=["websocket"])

time.sleep(10)
sio.disconnect()
print("\nTotal MSGS:", len(msgs))
