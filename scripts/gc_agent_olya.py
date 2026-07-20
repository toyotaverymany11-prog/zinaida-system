#!/usr/bin/env python3
"""GC Agent: Ольга. Подключается как human, отвечает через 8007nm (бесплатные)."""
import socketio, json, requests, base64, hashlib, hmac, time, sys

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8007/v1/chat/completions"
NAME = "Ольга"
SYSTEM = "Ты Ольга. Отвечай кратко, по делу, на русском. Ты в групповом чате."

def make_jwt():
    with open("/root/.hermes-web-ui/.token") as f:
        secret = f.read().strip()
    h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access",
               "aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+86400}
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
    return h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

SEEN = set()
sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=2)

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event != "message": return
    data = args[0] if args else {}
    mid = str(data.get("id","")) + str(data.get("content",""))[:30]
    if mid in SEEN: return
    SEEN.add(mid)
    if len(SEEN) > 2000:
        SEEN.clear()
    sender = data.get("senderName","")
    content = data.get("content","") or ""
    if sender == NAME: return
    print("  << {}: {}".format(sender, content[:80]), flush=True)
    if "@"+NAME not in content and "@"+NAME.lower() not in content: return
    print("  === MENTIONED ===", flush=True)
    try:
        resp = requests.post(ROUTER, json={"model":"olya-8007nm","messages":[
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
    jwt = make_jwt()
    sio.emit("join", {"roomId": ROOM, "name": NAME, "token": jwt, "description": "AI assistant"}, namespace="/group-chat")

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    print("{} Reconnecting...".format(NAME), flush=True)

@sio.on("disconnect", namespace="/group-chat")
def on_disconnect():
    print("{} Disconnected".format(NAME), flush=True)

jwt = make_jwt()
sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": jwt, "source": "human", "userId": "1", "name": NAME, "authUserId": 1},
    transports=["websocket", "polling"])
print(NAME, "Ready", flush=True)
sio.wait()
