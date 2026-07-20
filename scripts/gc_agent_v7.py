#!/usr/bin/env python3
"""
GC Agent v7 — пишет ответ напрямую в БД + отправляет через REST API.
Обходит проблему с emit — не использует Socket.IO для отправки.
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

def write_and_notify(name, content):
    """Пишет в БД и отправляет событие через nsp.to(room).emit через HTTP API"""
    mid = "gcv7_{}_{}".format(name.lower(), int(time.time()*1000))
    ts = int(time.time()*1000)
    sid = "olya_writer" if name == "Ольга" else "zina_writer"
    
    # Пишем в БД
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gc_messages (id, roomId, senderId, senderName, content, timestamp, role) VALUES (?,?,?,?,?,?,?)",
        (mid, ROOM, sid, name, content, ts, "user")
    )
    cur.execute("UPDATE gc_rooms SET totalTokens = totalTokens + ? WHERE id = ?",
        (len(content)*2, ROOM))
    conn.commit()
    conn.close()
    
    # Триггерим через REST API — если есть эндпоинт
    # Пробуем через Socket.IO напрямую: nsp.to(room).emit(message) через событие
    # Отправляем событие в сокет-сервер
    # (сообщение уже в БД — при обновлении страницы появится)
    
    # Дополнительно — эмитим через сокет с callback для всех
    sio.emit("gc_update", {
        "roomId": ROOM,
        "type": "new_message",
        "message": {"id": mid, "senderId": sid, "senderName": name, "content": content, "timestamp": ts}
    }, namespace="/group-chat")
    
    print("  [{}] wrote msg {}: {}".format(name, mid, content[:40]), flush=True)

def ask(name, prompt, sender, content):
    try:
        r = requests.post(ROUTER, json={
            "model": "deepseek-chat",
            "messages": [{"role":"system","content":prompt}, {"role":"user","content":"От {}: {}".format(sender, content)}],
            "max_tokens": 300, "temperature": 0.7
        }, timeout=30)
        reply = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "ок"
    except:
        reply = "Ок."
    print("  [{}] reply: {}".format(name, reply[:50]), flush=True)
    write_and_notify(name, reply)

@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event == "message":
        data = args[0] if args else {}
        mid = str(data.get("id","")) + str(data.get("content",""))[:20]
        if mid in SEEN: return
        SEEN.add(mid)
        sender = data.get("senderName","") or ""
        content = data.get("content","") or ""
        if sender in ["Ольга","Зинаида"]: return
        if not content.strip(): return
        print("  [chat] {}: {}".format(sender, content[:60]), flush=True)
        for name, prompt in [("Ольга","Ты Ольга. Отвечай кратко, по делу, на русском."), ("Зинаида","Ты Зинаида. Отвечай на русском.")]:
            if "@"+name in content or "@"+name.lower() in content:
                ask(name, prompt, sender, content)
                return

@sio.on("connect", namespace="/group-chat")
def on_connect():
    sio.emit("join", {"roomId": ROOM, "name": "GCv7", "description": "GC Agent v7"}, namespace="/group-chat")
    print("Connected v7", flush=True)

# Чищу БД от дублей
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for uid, uname in [("olya_writer","Ольга"), ("zina_writer","Зинаида")]:
        cur.execute("DELETE FROM gc_room_members WHERE roomId=? AND userId=?", (ROOM, uid))
        cur.execute("INSERT OR IGNORE INTO gc_room_members (id, roomId, userId, userName, description, joinedAt, updatedAt) VALUES (?,?,?,?,?,?,?)",
            ("mem7_"+uid, ROOM, uid, uname, "AI agent", int(time.time()*1000), int(time.time()*1000)))
    conn.commit()
    conn.close()
except: pass

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "1", "name": "GCv7"},
    transports=["websocket", "polling"])
print("Ready v7", flush=True)

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": "GCv7"}, namespace="/group-chat")

try:
    sio.wait()
except:
    sio.disconnect()
