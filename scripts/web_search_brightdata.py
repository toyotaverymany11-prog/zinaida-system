#!/usr/bin/env python3
"""search via BrightData SERP API"""
import urllib.request, urllib.parse, json, sys, os, re, html

def load_key():
    for p in ["/root/.hermes/.env", "/opt/zinaida/.env", "/opt/zinaida/meta_agent/.env"]:
        try:
            with open(p) as f:
                for line in f:
                    if "BRIGHTDATA_KEY" in line:
                        return line.split("=",1)[1].strip().strip('"\n\r ')
        except: pass
    return ""

API_KEY=load_key()

def search(query, limit=5):
    if not API_KEY: return {"error": "BRIGHTDATA_KEY not found", "results": []}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={min(limit,10)}&hl=ru"
    payload = {"zone": "serp_api1", "url": search_url, "format": "raw", "data_format": "html"}
    try:
        req = urllib.request.Request("https://api.brightdata.com/request", data=json.dumps(payload).encode(), headers=headers)
        resp = urllib.request.urlopen(req, timeout=30)
        h = resp.read().decode("utf-8", errors="replace")
        
        results = []
        # Ищем h3 (заголовки результатов)
        for m in re.finditer(r'<h3[^>]*>(.*?)</h3>', h):
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            r_entity = {"title": title, "link": "", "snippet": ""}
            # Ищем ссылку рядом с этим h3
            ctx = h[max(0, m.start()-2000):m.end()+2000]
            for lm in re.finditer(r'href="(https?://[^"]+)"', ctx):
                l = lm.group(1)
                if not any(x in l for x in ['google.com/search', 'accounts.google', 'policies.google', 'google.com/url']):
                    r_entity["link"] = l.split('&')[0]
                    break
            # Ищем сниппет рядом
            for sm in re.finditer(r'class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>', ctx):
                s = re.sub(r'<[^>]+>', '', sm.group(1)).strip()
                if len(s) > 15:
                    r_entity["snippet"] = s[:200]
                    break
            if title and len(title) > 3:
                results.append(r_entity)
                if len(results) >= limit: break
        
        return {"results": results, "total": len(results)}
    except Exception as e:
        return {"error": str(e)[:300], "results": []}

def extract(url):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {"zone": "serp_api1", "url": url, "format": "raw", "data_format": "html"}
    try:
        req = urllib.request.Request("https://api.brightdata.com/request", data=json.dumps(payload).encode(), headers=headers)
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()[:8000]
        return {"url": url, "content": text, "len": len(text)}
    except Exception as e:
        return {"url": url, "error": str(e)[:200]}

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--extract" in args:
        i = args.index("--extract")
        print(json.dumps(extract(args[i+1]), ensure_ascii=False, indent=2))
    elif args:
        l = 5
        if "--limit" in args: l = int(args[args.index("--limit")+1])
        print(json.dumps(search(args[0], l), ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "python3 web_search_brightdata.py 'запрос'"}, ensure_ascii=False, indent=2))
