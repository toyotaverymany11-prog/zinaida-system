#!/usr/bin/env python3
"""
GC Agent v5 — два сокета: один слушает (super_admin), второй пишет (другой userId).
Сообщение от Ольги пишется через второй сокет с userId=olya_writer.
"""
import socketio, json, requests, base64, hashlib, hmac, time, sys, threading

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"

def make_jwt():
    with open("/root/.hermes-web-ui/.token") as f: secret = f.read().strip()
    h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps({"sub":"1","username":"ZinaidaSecure2026","role":"super_admin","type":"access","aud":"hermes-web-ui","iat":int(time.time()),"exp":int(time.time())+86400}).encode()).rstrip(b"=").decode()
    s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
    return h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

JWT = make_jwt()

# Пул сообщений для отправки
send_queue = []

def send_worker():
    """Отдельный поток — пишет сообщения в комнату от имени разных userId"""
    while True:
        time.sleep(0.5)
        while send_queue:
            name, content = send_queue.pop(0)
            try:
                # Создаём временное соединение для каждого сообщения
                ws = socketio.Client()
                uid = "olya_writer" if name == "Ольга" else "zina_writer"
                
                @ws.on("connect", namespace="/group-chat")
                def on_c(uid=uid, name=name, content=content, ws=ws):
                    ws.emit("join", {"roomId": ROOM, "name": name}, namespace="/group-chat",
                           callback=lambda d: None)
                    time.sleep(0.3)
                    ws.emit("message", {
                        "roomId": ROOM, "content": content,
                        "id": "send_{}_{}".format(name, int(time.time()*1000))
                    }, namespace="/group-chat")
                    time.sleep(0.5)
                    ws.disconnect()
                
                ws.connect(WEB_UI, namespaces=["/group-chat"],
                    auth={"token": JWT, "source": "human", "userId": uid, "name": name},
                    transports=["polling"], wait_timeout=3)
            except Exception as e:
                print("  !! send {} fail: {}".format(name, e), flush=True)

threading.Thread(target=send_worker, daemon=True).start()

# Debug: проверяю что в БД есть пользователь olya_writer
import sqlite3
try:
    conn = sqlite3.connect("/root/.hermes-web-ui/hermes-web-ui.db")
    cur = conn.cursor()
    for uid, uname in [("olya_writer","Ольга"), ("zina_writer","Зинаида")]:
        cur.execute("SELECT id FROM gc_room_members WHERE roomId=? AND userId=?", (ROOM, uid))
        if not cur.fetchone():
            mid = "mem_{}".format(int(time.time()*1000))
            cur.execute("INSERT INTO gc_room_members (id, roomId, userId, userName, description, joinedAt, updatedAt) VALUES (?,?,?,?,?,?,?)",
                (mid, ROOM, uid, uname, "AI agent", int(time.time()*1000), int(time.time()*1000)))
            print("Added {} to members".format(uname), flush=True)
    conn.commit()
    conn.close()
except Exception as e:
    print("DB: {}".format(e), flush=True)

# Основной слушающий сокет
sio = socketio.Client()
SEEN = set()

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
    
    for name in ["Ольга","Зинаида"]:
        if "@" + name in content or "@" + name.lower() in content:
            print("  [chat] {} -> @{}: {}".format(sender, name, content[:60]), flush=True)
            try:
                r = requests.post(ROUTER, json={
                    "model": "deepseek-chat",
                    "messages": [{"role":"system","content":"Ты {}. Отвечай кратко, на русском.".format(name)},
                                {"role":"user","content":"От {}: {}".format(sender, content)}],
                    "max_tokens": 300, "temperature": 0.7
                }, timeout=30)
                reply = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "Ок, поняла."
            except:
                reply = "Ок."
            print("  [{}] >> {}".format(name, reply[:50]), flush=True)
            send_queue.append((name, reply))

@sio.on("connect", namespace="/group-chat")
def on_connect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026"}, namespace="/group-chat")
    print("Listener connected", flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={"token": JWT, "source": "human", "userId": "1", "name": "ZinaidaSecure2026"},
    transports=["websocket", "polling"])
print("Ready", flush=True)

@sio.on("reconnect", namespace="/group-chat")
def on_reconnect():
    sio.emit("join", {"roomId": ROOM, "name": "ZinaidaSecure2026"}, namespace="/group-chat")

try:
    sio.wait()
except:
    sio.disconnect()
