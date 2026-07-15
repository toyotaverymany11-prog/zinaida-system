#!/usr/bin/env python3
"""Правильная проверка всех провайдеров"""
import urllib.request, json, ssl, time

def read_key(name):
    for path in ["/opt/zinaida/.env", "/opt/zinaida/meta_agent/.env"]:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(name) and "=" in line:
                    eq = line.index("=")
                    val = line[eq+1:].strip().strip("'\"")
                    if val and val != "***" and len(val) > 5:
                        return val
    return ""

print("=" * 50)
print("PROVIDER CHECK (correct calls)")
print("=" * 50)

# 1. GitHub
print("\n1. GitHub Models (gpt-4o-mini):")
for name in ["GITHUB_TOKEN", "GITHUB_TOKEN_2"]:
    key = read_key(name)
    if not key: continue
    try:
        data = json.dumps({"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hi, one word"}],"max_tokens":5}).encode()
        req = urllib.request.Request("https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21",
            data=data, headers={"Authorization":"Bearer "+key, "Content-Type":"application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        print("  ["+name+"] OK: "+r["choices"][0]["message"]["content"][:30])
    except urllib.error.HTTPError as e:
        print("  ["+name+"] HTTP "+str(e.code)+": "+e.reason[:60])

# 2. Mistral
print("\n2. Mistral:")
for name in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2", "MISTRAL_API_KEY_3"]:
    key = read_key(name)
    if not key: continue
    try:
        data = json.dumps({"model":"mistral-small-latest","messages":[{"role":"user","content":"Hi, one word"}],"max_tokens":5}).encode()
        req = urllib.request.Request("https://api.mistral.ai/v1/chat/completions",
            data=data, headers={"Authorization":"Bearer "+key, "Content-Type":"application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        print("  ["+name+"] OK: "+r["choices"][0]["message"]["content"][:30])
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:80]
        print("  ["+name+"] HTTP "+str(e.code)+": "+body)

# 3. Ollama
print("\n3. Ollama:")
for name in ["OLLAMA_API_KEY", "OLLAMA_API_KEY_2", "GREG_OLLAMA_KEY"]:
    key = read_key(name)
    if not key: continue
    for url in ["https://ollama.com/v1/chat/completions", "https://api.ollama.com/v1/chat/completions"]:
        try:
            data = json.dumps({"model":"gemma3:4b","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}).encode()
            req = urllib.request.Request(url, data=data, 
                headers={"Authorization":"Bearer "+key, "Content-Type":"application/json"}, method="POST")
            resp = urllib.request.urlopen(req, timeout=10)
            r = json.loads(resp.read())
            short = r["choices"][0]["message"]["content"][:30]
            print("  ["+name+"] OK via "+url.split("/")[2]+": "+short)
            break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("  ["+name+"] HTTP 401 Unauthorized via "+url.split("/")[2])
                break
            print("  ["+name+"] HTTP "+str(e.code)+" via "+url.split("/")[2])

# 4. GigaChat
print("\n4. GigaChat (OAuth2):")
giga_key = read_key("GIGACHAT_CLIENT_SECRET")
if not giga_key:
    giga_key = read_key("GIGACHAT_AUTH_KEY")
if giga_key:
    ctx = ssl._create_unverified_context()
    try:
        auth_data = "scope=GIGACHAT_API_PERS".encode()
        auth_headers = {
            "Authorization": "Basic "+giga_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": "019d967c-5279-7677-bd29-e4e26eb88431"
        }
        auth_req = urllib.request.Request("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            data=auth_data, headers=auth_headers, method="POST")
        with urllib.request.urlopen(auth_req, context=ctx, timeout=15) as resp:
            token = json.loads(resp.read())["access_token"]
            print("  OAuth2 token OK ("+str(len(token))+" chars)")
        
        time.sleep(2)
        
        chat_data = json.dumps({"model":"GigaChat:latest","messages":[{"role":"user","content":"Hi, one word"}],"max_tokens":5}).encode()
        chat_headers = {"Authorization": "Bearer "+token, "Content-Type": "application/json"}
        chat_req = urllib.request.Request("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            data=chat_data, headers=chat_headers, method="POST")
        with urllib.request.urlopen(chat_req, context=ctx, timeout=20) as resp:
            r = json.loads(resp.read())
            print("  Chat OK: "+r["choices"][0]["message"]["content"][:30])
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:150]
        print("  HTTP "+str(e.code)+": "+body[:80])
    except Exception as e:
        print("  "+type(e).__name__+": "+str(e)[:100])
else:
    print("  GIGACHAT_CLIENT_SECRET not found")

# 5. Zhipu
print("\n5. Zhipu:")
zhipu_key = read_key("ZHIPU_API_KEY")
if zhipu_key:
    try:
        data = json.dumps({"model":"glm-4-flash","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}).encode()
        req = urllib.request.Request("https://open.bigmodel.cn/api/paas/v4/chat/completions",
            data=data, headers={"Authorization":"Bearer "+zhipu_key, "Content-Type":"application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        print("  OK: "+r["choices"][0]["message"]["content"][:30])
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:100]
        print("  HTTP "+str(e.code)+": "+body[:80])
else:
    print("  ZHIPU_API_KEY not found")

print("\nDone")
