#!/usr/bin/env python3
"""
Zinaida VK Session Manager — вход в VK, dev.vk.com, id.vk.com
с сохранением полной сессии. 

Сценарий: ты заходишь на VK через браузер, я сохраняю куки.

Использование:
  python3 vk_session.py login    — откроет страницу логина VK, ты входишь
  python3 vk_session.py open <URL> — открыть страницу от имени вошедшего
  python3 vk_session.py settings  — открыть настройки приложения 54567827
  python3 vk_session.py find_redirect  — найти поле redirect_uri в настройках
"""

import sys, os, json
sys.path.insert(0, "/opt/zinaida/scripts")
from session_browser import open_url, login_with_qr, SESSIONS_DIR
from pathlib import Path


def open_settings():
    """Открыть настройки приложения 54567827"""
    open_url("https://dev.vk.com/ru/admin/app-settings/54567827", 
             session_name="vk", take_screenshot=True)


def find_redirect_uri():
    """Открыть настройки и попытаться найти поле redirect_uri/доверенный URL"""
    from playwright.sync_api import sync_playwright
    
    session_path = SESSIONS_DIR / "vk.json"
    if not session_path.exists():
        print("❌ Нет сессии 'vk'. Сначала: python3 vk_session.py login")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = json.loads(session_path.read_text())
        context.add_cookies(cookies)
        page = context.new_page()
        
        # Пробуем разные URL настроек
        urls = [
            "https://dev.vk.com/ru/admin/app-settings/54567827",
            "https://dev.vk.com/ru/admin/app-settings/54567827/info",
            "https://dev.vk.com/ru/admin/app-settings/54567827/settings",
        ]
        
        for url in urls:
            print(f"\n🔍 {url}")
            page.goto(url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            
            final_url = page.url
            print(f"   Финальный URL: {final_url[:150]}")
            
            body = page.inner_text("body")
            if "404" not in body[:50]:
                print(f"   ✅ Страница доступна!")
                print(f"   Контент:")
                for line in body.split("\n"):
                    l = line.strip()
                    if l and any(w in l.lower() for w in ["redirect", "url", "uri", "базов", "домен", "довер", "oauth"]):
                        print(f"     🔑 {l[:200]}")
                
                # Сохраняем скрин
                page.screenshot(path=f"/tmp/vk_settings_{url.rstrip('/').split('/')[-1]}.png", full_page=True)
            else:
                print(f"   ❌ 404 — нет доступа")
        
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "login":
        login_with_qr("https://vk.com", session_name="vk")
        print("\n✅ Сессия VK сохранена. Теперь можно:")
        print("  python3 vk_session.py settings — открыть настройки приложения")
        print("  python3 vk_session.py open <URL> — открыть любую страницу VK")
    
    elif cmd == "open":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        if not url:
            print("❌ Укажи URL")
            sys.exit(1)
        open_url(url, session_name="vk", take_screenshot=True)
    
    elif cmd == "settings":
        open_settings()
    
    elif cmd == "find_redirect":
        find_redirect_uri()
    
    elif cmd == "dev":
        open_url("https://dev.vk.com/ru", session_name="vk")
    
    else:
        print(f"❌ Неизвестная команда: {cmd}")
