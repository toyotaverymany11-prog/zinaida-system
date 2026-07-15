#!/usr/bin/env python3
"""Group Chat @Olya responder. Слушает комнату, отвечает на @Оля."""
import socketio, json, base64, hashlib, hmac, time, sys

WEB_UI_URL = "http://127.0.0.1:8648"
ROOM_ID = "mrj9nkx8nln7lx"

def get_jwt():
    with open("/root/.hermes-web-ui/.token") as f:
        s = f.read().strip()
    h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps({
        "sub":"1","username":"ZinaidaSecure2026","role":"super_admin",
        "type":"access","aud":"hermes-web-ui",
        "iat":int(time.time()),"exp":int(time.time())+86400
    }).encode()).rstrip(b"=").decode()
    sig = hmac.new(s.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

def run():
    sio = socketio.Client()
    seen = set()
    
    @sio.on("*", namespace="/group-chat")
    def handler(event, *args):
        if event != "message":
            return
        data = args[0] if args else {}
        msg_id = data.get("id", "")
        if msg_id in seen:
            return
        seen.add(msg_id)
        
        sender = data.get("senderId", "")
        content = data.get("content", "")
        name = data.get("senderName", "user")
        
        # Пропускаем свои сообщения и без @Оля
        if sender == "auth:1":
            return
        if "@Оля" not in content and "@оля" not in content and "@olya" not in content:
            return
        
        print(f"<< @Оля from {name}: {content[:80]}", flush=True)
        
        # Отвечаем
        response = f"@{name}, слушаю! Сообщение принято."
        sio.emit("message", {"roomId": ROOM_ID, "content": response}, namespace="/group-chat")
        print(f">> Ответ отправлен: {response[:60]}", flush=True)
    
    @sio.on("connect", namespace="/group-chat")
    def connect():
        sio.emit("join", {"roomId": ROOM_ID}, namespace="/group-chat")
        print("Connect/join OK", flush=True)
    
    sio.connect(WEB_UI_URL, namespaces=["/group-chat"], auth={"token": get_jwt()})
    print("OK. Слушаю...", flush=True)
    sio.wait()

if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception as e:
            print(f"Restart: {e}", flush=True)
            time.sleep(5)
