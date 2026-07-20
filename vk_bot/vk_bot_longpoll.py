import requests
import time

VK_TOKEN = "vk1.a.3P4n_85bP-Xmg8rWztGYx3wOoRlAcpy-J8q-B3MyUhUeK58cdgOUnLJp87kil8n14PUcIny7WxC291CTAtOIlbl6PUuR_20ILnEwcFi_LNdTt1gpBCDiwT0gEHWEZvqz2tnQPRwFWfl-NmY6jz_QZ9QEsVI7O7Dvfx1pJIZ2PSbhrWWtDOMv51WFbIrxfi9RaC1pQdIbwHnb7EIdhaaDpg"
GROUP_ID = "237663277"
N8N_WEBHOOK = "http://localhost:5678/webhook/zinaida-webhook"

def get_longpoll_server():
    r = requests.post("https://api.vk.com/method/groups.getLongPollServer", data={
        "group_id": GROUP_ID, "access_token": VK_TOKEN, "v": "5.199"
    })
    result = r.json()
    if "error" in result:
        print(f"ОШИБКА: {result['error']}")
        exit(1)
    return result["response"]

def send_vk(uid, text):
    try:
        requests.post("https://api.vk.com/method/messages.send", data={
            "user_id": uid, "message": text,
            "random_id": int(time.time()*1000),
            "access_token": VK_TOKEN, "v": "5.199"
        }, timeout=5)
    except: pass

def main():
    print("=== VK Long Poll бот запущен ===")
    server = get_longpoll_server()
    ts = server["ts"]
    print(f"Server: {server['server']}, Ожидание...")
    
    while True:
        try:
            r = requests.get(server["server"], params={
                "act": "a_check", "key": server["key"], "ts": ts, "wait": 25
            }, timeout=30)
            data = r.json()
            if "failed" in data:
                print("Long Poll failed, переподключение...")
                server = get_longpoll_server()
                ts = server["ts"]
                continue
            ts = data["ts"]
            for event in data.get("updates", []):
                if event["type"] == "message_new":
                    msg = event["object"]["message"]
                    uid = msg["from_id"]
                    text = msg.get("text", "")
                    print(f"[{time.strftime('%H:%M:%S')}] {uid}: {text}")
                    
                    # Пробуем получить ответ от n8n
                    try:
                        resp = requests.post(N8N_WEBHOOK, json={"message": text, "user_id": uid}, timeout=10)
                        n8n_reply = resp.json().get("message", "")
                        # Если n8n вернул ерунду на английском — отвечаем по-русски
                        if not n8n_reply or "Workflow" in n8n_reply or len(n8n_reply) < 5:
                            reply = "Привет! Я Зинаида. Чем помочь?"
                        else:
                            reply = n8n_reply
                    except:
                        reply = "Привет! Я Зинаида. Чем помочь?"
                    
                    send_vk(uid, reply)
                    print(f"[{time.strftime('%H:%M:%S')}] Ответ: {reply}")
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
