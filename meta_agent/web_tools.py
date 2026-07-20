import os
import sys
import json
import time
import sqlite3
import requests
import warnings
from duckduckgo_search import DDGS

warnings.filterwarnings("ignore")

KEYS_PATH = "/opt/zinaida/sandbox/configs/api_keys.json"
QUOTAS_DB = "/opt/zinaida/meta_agent/quotas.db"
CACHE_DIR = "/opt/zinaida/cache/web"

def _get_tavily_key():
    try:
        with open(KEYS_PATH, "r", encoding="utf-8") as f:
            keys = json.load(f)
            return keys.get("tavily", "")
    except Exception:
        return ""

TAVILY_KEY = _get_tavily_key()

def _check_and_consume_quota():
    try:
        conn = sqlite3.connect(QUOTAS_DB)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        cur = conn.execute("SELECT used, limit_val, reset_time FROM quotas WHERE provider='web_search'")
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        used, limit_val, reset_time = row
        now = int(time.time())
        if now > reset_time:
            conn.execute("UPDATE quotas SET used=1, reset_time=? WHERE provider='web_search'", (now + 86400,))
            conn.commit()
            conn.close()
            return True
        if used >= limit_val:
            conn.close()
            return False
        conn.execute("UPDATE quotas SET used=used+1 WHERE provider='web_search'")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def _read_cache(query_hash):
    cache_file = os.path.join(CACHE_DIR, f"{query_hash}.json")
    try:
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 86400:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
    except Exception:
        pass
    return None

def _write_cache(query_hash, data):
    cache_file = os.path.join(CACHE_DIR, f"{query_hash}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def search_web(query, max_results=3):
    if not _check_and_consume_quota():
        return []

    results = []
    q_hash = str(hash(query))

    cached = _read_cache(q_hash)
    if cached:
        return cached

    # Пытаемся сначала через DuckDuckGo (бесплатно, без лимитов)
    try:
        with DDGS() as ddgs:
            ddg_res = list(ddgs.text(query, max_results=max_results))
            for item in ddg_res:
                results.append({"title": item.get("title", ""), "snippet": item.get("body", ""), "url": item.get("href", "")})
            if results:
                _write_cache(q_hash, results)
                return results
    except Exception:
        pass

    # Если DuckDuckGo не сработал - пробуем Tavily (с ключом, могут быть лимиты)
    if TAVILY_KEY:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_KEY, "query": query, "max_results": max_results},
                timeout=3
            )
            if resp.status_code == 429:
                pass
            else:
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", [])[:max_results]:
                    results.append({"title": item.get("title", ""), "snippet": item.get("content", ""), "url": item.get("url", "")})
                if results:
                    _write_cache(q_hash, results)
                    return results
        except Exception:
            pass

    try:
        with DDGS() as ddgs:
            ddg_res = list(ddgs.text(query, max_results=max_results))
            for item in ddg_res:
                results.append({"title": item.get("title", ""), "snippet": item.get("body", ""), "url": item.get("href", "")})
            if results:
                _write_cache(q_hash, results)
                return results
    except Exception:
        pass

    tech_markers = ["code", "api", "install", "hermes", "python", "github", "docs"]
    if any(m in query.lower() for m in tech_markers):
        try:
            gh_url = "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md"
            resp = requests.get(gh_url, timeout=3)
            resp.raise_for_status()
            text = resp.text[:2000]
            results.append({"title": "GitHub Hermes README", "snippet": text, "url": gh_url})
            _write_cache(q_hash, results)
            return results
        except Exception:
            pass

    return []
