#!/usr/bin/env python3
"""
GC Agent v3 — два процесса, по одному на агента.
Подключается как human, отвечает через DeepSeek.
"""
import socketio, json, requests, base64, hashlib, hmac, time, sys, os, subprocess

WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"

def make_jwt():
    with open("/root/.hermes-web-ui/.token") as f:
        secret = f.read().strip()
    h = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps({
        "sub":"1","username":"ZinaidaSecure2026","role":"super_admin",
        "type":"access","aud":"hermes-web-ui",
        "iat":int(time.time()),"exp":int(time.time())+86400
    }).encode()).rstrip(b"=").decode()
    s = hmac.new(secret.encode(), (h+"."+p).encode(), hashlib.sha256).digest()
    return h+"."+p+"."+base64.urlsafe_b64encode(s).rstrip(b"=").decode()

JWT = make_jwt()

class AgentProcess:
    """Запускает агента как отдельный Python-процесс"""
    def __init__(self, name, system_prompt, user_id):
        self.name = name
        self.user_id = user_id
        # Создаём скрипт для этого агента
        script = """#!/usr/bin/env python3
import socketio, json, requests, base64, hashlib, hmac, time, sys
WEB_UI = "http://127.0.0.1:8648"
ROOM = "mrj9nkx8nln7lx"
ROUTER = "http://127.0.0.1:8003/v1/chat/completions"
NAME = "{name}"
SYSTEM = {system_prompt!r}
JWT = {jwt!r}
SEEN = set()

def ask_ai(content, sender):
    try:
        resp = requests.post(ROUTER, json={{"model":"deepseek-chat","messages":[
            {{"role":"system","content":SYSTEM}},
            {{"role":"user","content":"Сообщение от {sender} в чате: «{content}»"}}
        ],"max_tokens":500,"temperature":0.7,"stream":False}}, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("choices",[{{}}])[0].get("message",{{}}).get("content","")
        return "(HTTP {{}})".format(resp.status_code)
    except Exception as e:
        return "(err: {{}})".format(e)

sio = socketio.Client()
@sio.on("*", namespace="/group-chat")
def on_all(event, *args):
    if event != "message": return
    data = args[0] if args else {{}}
    mid = str(data.get("id","")) + str(data.get("content",""))[:30]
    if mid in SEEN: return
    SEEN.add(mid)
    sender = data.get("senderName","")
    content = data.get("content","") or ""
    if sender == NAME: return
    print("  << {{}}: {{}}".format(sender, content[:80]), flush=True)
    mentions = ["@{{}}".format(NAME), "@{{}}".format(NAME.lower())]
    if not any(m in content for m in mentions): return
    print("  === MENTIONED ===", flush=True)
    resp = ask_ai(content, sender)
    print("  >> {{}}".format(resp[:80]), flush=True)
    sio.emit("message", {{"roomId": ROOM, "content": resp}}, namespace="/group-chat")

@sio.on("connect", namespace="/group-chat")
def on_connect():
    print("Connected as {{}}".format(NAME), flush=True)
    sio.emit("join", {{"roomId": ROOM, "name": NAME}}, namespace="/group-chat")
    print("Joined {{}}".format(ROOM), flush=True)

sio.connect(WEB_UI, namespaces=["/group-chat"],
    auth={{"token": JWT, "source": "human", "userId": "{user_id}"}},
    transports=["websocket"])
print("{{}} Ready".format(NAME), flush=True)
sio.wait()
""".format(name=self.name, system_prompt=system_prompt, jwt=JWT, user_id=self.user_id)
        
        script_path = "/opt/zinaida/scripts/gc_agent_{}.py".format(self.name.lower())
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        
        print("{} → {}".format(self.name, script_path), flush=True)

# Создаём скрипты для двух агентов
AgentProcess("Ольга", "Ты Ольга. Отвечай кратко, по делу, на русском. Ты в групповом чате.", "olya_agent")
AgentProcess("Зинаида", "Ты Зинаида. Отвечай на русском. Ты в групповом чате.", "zinaida_agent")

print("Скрипты созданы", flush=True)
