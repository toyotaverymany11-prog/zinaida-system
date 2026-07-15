#!/usr/bin/env python3
"""GC Agent: Ольга. Подключается как human, отвечает через DeepSeek."""
import socketio, json, requests, base64, hashlib, hmac, time, sys

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"
NAME = "Ольга"
SYSTEM = "Ты Ольга. Отвечай кратко, по делу, на русском. Ты в групповом чате."
USER_ID = "olya_agent"

with open("/root/.hermes-web-ui/.token") as f: secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+86400}
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
JWT = h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

SEEN = set()
sio = socketio.Client()

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event != "message": return
    data = args[0] if args else {}
    mid = str(data.get("id","")) + str(data.get("content",""))[:30]
    if mid in SEEN: return
    SEEN.add(mid)
    sender = data.get("senderName","")
    content = data.get("content","") or ""
    if sender == NAME: return
    print("  << {}: {}".format(sender, content[:80]), flush=True)
    if "@"+NAME not in content and "@"+NAME.lower() not in content: return
    print("  === MENTIONED ===", flush=True)
    try:
        resp = requests.post(ROUTER, json={"model":"deepseek-chat","messages":[
            {"role":"system","content":SYSTEM},
            {"role":"user","content":"Сообщение от {} в чате: «{}»".format(sender, content)}
        ],"max_tokens":500,"temperature":0.7}, timeout=30)
        reply = resp.json()["choices"][0]["message"]["content"] if resp.status_code==200 else "(HTTP {})".format(resp.status_code)
    except Exception as e:
        reply = "(err: {})".format(e)
    print("  >> {}".format(reply[:80]), flush=True)
    sio.emit("message", {"roomId": ROOM, "content": reply, "id": "olya_{}".format(int(time.time()*1000))}, namespace="/group-chat")

@sio.on("connect", namespace="/group-chat")
def on_connect():
    print("Connected as", NAME, flush=True)
    sio.emit("join", {"roomId": ROOM, "name": NAME, "description": "AI assistant"}, namespace="/group-chat")

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "1", "name": "Ольга", "authUserId": 1},
    transports=["websocket", "polling"])
print(NAME, "Ready", flush=True)

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": NAME, "description": "AI assistant"}, namespace="/group-chat")
    print("{} Rejoined".format(NAME), flush=True)

sio.wait()
