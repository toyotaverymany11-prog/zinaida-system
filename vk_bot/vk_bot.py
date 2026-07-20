from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)
VK_TOKEN = "vk1.a.3P4n_85bP-Xmg8rWztGYx3wOoRlAcpy-J8q-B3MyUhUeK58cdgOUnLJp87kil8n14PUcIny7WxC291CTAtOIlbl6PUuR_20ILnEwcFi_LNdTt1gpBCDiwT0gEHWEZvqz2tnQPRwFWfl-NmY6jz_QZ9QEsVI7O7Dvfx1pJIZ2PSbhrWWtDOMv51WFbIrxfi9RaC1pQdIbwHnb7EIdhaaDpg"
N8N_URL = "http://localhost:5678/webhook/zinaida-webhook"

def send_vk(uid, text):
    requests.post("https://api.vk.com/method/messages.send", 
        data={"access_token": VK_TOKEN, "user_id": uid, 
              "message": text, "random_id": int(os.time()*1000), "v": "5.199"})

@app.route('/vk_webhook', methods=['GET','POST'])
def webhook():
    if request.method == 'GET': return "OK"
    data = request.get_json(silent=True) or {}
    if data.get('type') == 'confirmation': return '072f5212', 200
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        uid = msg['from_id']
        text = msg.get('text', '')
        try:
            r = requests.post(N8N_URL, json={"message": text}, timeout=5)
            reply = r.json().get('message', 'Привет!')
            send_vk(uid, reply)
        except: 
            send_vk(uid, 'OK')
    return jsonify({"ok":1}), 200

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5000)
