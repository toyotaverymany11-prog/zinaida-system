#!/usr/bin/env python3
"""
GC Agent v6 — один процесс, один сокет.
Подключается как auth:1 (super_admin), пишет в БД сообщения напрямую.
Отвечает на @Ольга и @Зинаида через DeepSeek.
"""
import socketio, json, requests, base64, hashlib, hmac, time, sys, sqlite3

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"
DB = "/root/.hermes-web-ui/hermes-web-ui.db"

with open("/root/.hermes-web-ui/.token") as f:
    secret = f.read().strip()
h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
payload = {"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+86400}
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
JWT = h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

SEEN = set()
sio = socketio.Client()

def write_message_db(name, content):
    """Пишет сообщение напрямую в БД и триггерит событие через сокет"""
    mid = "gc_{}_{}".format(name.lower(), int(time.time()*1000))
    ts = int(time.time()*1000)
    sid = "olya_writer" if name == "Ольга" else "zina_writer"
    
    # Пишем в БД
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO gc_messages (id, roomId, senderId, senderName, content, timestamp, role) VALUES (?,?,?,?,?,?,?)",
            (mid, ROOM, sid, name, content, ts, "user")
        )
        # Обновляем totalTokens
        cur.execute("UPDATE gc_rooms SET totalTokens = totalTokens + ? WHERE id = ?",
            (len(content) * 2, ROOM))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB error: {}".format(e), flush=True)
        return mid
    
    # Триггерим событие через сокет
    sio.emit("message", {
        "roomId": ROOM, "content": content,
        "id": mid, "senderName": name,
        "timestamp": ts
    }, namespace="/group-chat")
    
    return mid

def ask(name, prompt, sender, content):
    try:
        r = requests.post(ROUTER, json={
            "model": "deepseek-chat",
            "messages": [
                {"role":"system","content":prompt},
                {"role":"user","content":"От {}: {}".format(sender, content)}
            ],
            "max_tokens": 300, "temperature": 0.7
        }, timeout=30)
        reply = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "ок"
    except:
        reply = "Ок."
    print("  [{}] >> {}".format(name, reply[:60]), flush=True)
    write_message_db(name, reply)

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event != "message": return
    data = args[0] if args else {}
    mid = str(data.get("id","")) + str(data.get("content",""))[:20]
    if mid in SEEN: return
    SEEN.add(mid)
    sender = data.get("senderName","") or ""
    content = data.get("content","") or ""
    if sender in ["Ольга","Зинаида"]: return
    if not content.strip(): return
    print("  [chat] {}: {}".format(sender, content[:60]), flush=True)
    
    if "@Ольга" in content or "@ольга" in content:
        ask("Ольга", "Ты Ольга. Отвечай кратко, по делу, на русском.", sender, content)
    if "@Зинаида" in content or "@зинаида" in content:
        ask("Зинаида", "Ты Зинаида. Отвечай на русском.", sender, content)

@sio.on("connect", namespace="/group-chat")
def on_connect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026"}, namespace="/group-chat")
    print("Connected, joined {}".format(ROOM), flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "1", "name": "ZinaidaSecure2026"},
    transports=["websocket", "polling"])
print("Ready. Listening @Ольга @Зинаида", flush=True)

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026"}, namespace="/group-chat")

try:
    sio.wait()
except:
    sio.disconnect()
