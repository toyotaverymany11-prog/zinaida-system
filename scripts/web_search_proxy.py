#!/usr/bin/env python3
"""
Веб-поиск через Google Custom Search JSON API.
Использование:
  python3 web_search_proxy.py "запрос" [--limit 5]
  python3 web_search_proxy.py --extract "https://example.com"
"""

import urllib.request
import urllib.parse
import json
import sys
import time
import os
import re
import html

# Читаем ключ из .env файла напрямую
def load_google_key():
    env_files = [
        "/root/.hermes/.env",
        "/opt/zinaida/.env",
        "/opt/zinaida/meta_agent/.env",
        os.path.expanduser("~/.hermes/.env"),
    ]
    for env_path in env_files:
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except (FileNotFoundError, PermissionError):
            pass
    
    # Fallback: из config.yaml Hermes
    try:
        with open("/root/.hermes/config.yaml") as f:
            for line in f:
                if "api_key" in line and "AIza" in line:
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
    except:
        pass
    
    return ""

API_KEY = load_google_key()

def google_search(query, limit=5):
    """Поиск через Google Custom Search JSON API."""
    if not API_KEY:
        return {"error": "Нет API ключа Google. Положи в .env: GOOGLE_API_KEY=ваш_ключ", "results": []}
    
    # Проверяем что ключ похож на настоящий
    if not API_KEY.startswith("AIza"):
        return {"error": f"Ключ не похож на Google API ключ: {API_KEY[:10]}...", "results": []}

    results = []
    start = 1
    remaining = limit

    while remaining > 0:
        num = min(remaining, 10)
        url = (
            f"https://customsearch.googleapis.com/customsearch/v1"
            f"?key={API_KEY}"
            f"&q={urllib.parse.quote(query)}"
            f"&num={num}"
            f"&start={start}"
            f"&lr=lang_ru"
        )

        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            items = data.get("items", [])
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "").replace("\n", " ").strip(),
                })

            total = int(data.get("searchInformation", {}).get("totalResults", 0))
            if start + num > total or len(items) == 0:
                break

            start += num
            remaining -= len(items)
            time.sleep(0.2)

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                err = json.loads(body)
                msg = err.get("error", {}).get("message", body[:200])
            except:
                msg = body[:200]
            return {"error": f"HTTP {e.code}: {msg}", "results": results}
        except Exception as e:
            return {"error": str(e)[:200], "results": results}

    return {"results": results, "total": len(results)}


def extract_url(url):
    """Извлечение текста со страницы."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read().decode("utf-8", errors="replace")

        # Простая очистка HTML
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > 8000:
            text = text[:8000] + "..."

        return {"url": url, "content": text, "len": len(text)}
    except Exception as e:
        return {"url": url, "error": str(e)[:200]}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Использование: python3 web_search_proxy.py 'запрос' [--limit N] [--extract URL]"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    args = sys.argv[1:]

    if "--extract" in args:
        idx = args.index("--extract")
        url = args[idx + 1]
        result = extract_url(url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        query = args[0]
        limit = 5
        if "--limit" in args:
            idx = args.index("--limit")
            limit = int(args[idx + 1])
        result = google_search(query, limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
