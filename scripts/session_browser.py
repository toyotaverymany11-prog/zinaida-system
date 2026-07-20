#!/usr/bin/env python3
"""
Zinaida Session Browser — универсальный сессионный браузер на Playwright.
Позволяет:
1. Войти на любой сайт через QR-код или ссылку
2. Сохранить сессию в файл
3. Использовать сохранённую сессию для чтения страниц
4. Заходить на VK, dev.vk.com, id.vk.com и любые SPA

Использование:
  python3 session_browser.py login <URL> [--name vk]
  python3 session_browser.py open <URL> [--name vk] [--screenshot]
  python3 session_browser.py qr <URL> [--name vk]
  python3 session_browser.py list
  python3 session_browser.py delete <name>
"""

import json, sys, os, time
from pathlib import Path

# Путь к хранилищу сессий
SESSIONS_DIR = Path("/opt/zinaida/browser_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def get_session_path(name: str) -> Path:
    return SESSIONS_DIR / f"{name}.json"


def open_url(url: str, session_name: str = "default", take_screenshot: bool = False):
    """Открыть URL с сохранённой сессией (или без неё)"""
    from playwright.sync_api import sync_playwright
    
    session_path = get_session_path(session_name)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Загружаем сохранённые куки
        if session_path.exists():
            cookies = json.loads(session_path.read_text())
            context.add_cookies(cookies)
            print(f"📦 Загружена сессия '{session_name}': {len(cookies)} кук")
        else:
            print(f"🆕 Новая сессия '{session_name}' (без кук)")
        
        page = context.new_page()
        
        # Следим за редиректами
        responses = []
        page.on("response", lambda resp: responses.append(f"  {resp.status} {resp.url[:80]}"))
        
        print(f"🌐 Открываю: {url}")
        try:
            page.goto(url, timeout=45000, wait_until="networkidle")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️ Таймаут или ошибка загрузки: {e}")
        
        final_url = page.url
        print(f"📍 Финальный URL: {final_url[:150]}")
        
        # Сохраняем куки после загрузки
        cookies = context.cookies()
        session_path.write_text(json.dumps(cookies, indent=2))
        print(f"💾 Сохранено {len(cookies)} кук в сессию '{session_name}'")
        
        # Вытаскиваем текст
        body = page.inner_text("body")
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        
        print(f"\n📄 Контент страницы ({len(lines)} строк):")
        for line in lines[:80]:
            print(f"  {line[:200]}")
        
        if len(lines) > 80:
            print(f"  ... и ещё {len(lines) - 80} строк")
        
        # Скриншот если нужно
        if take_screenshot:
            screenshot_path = f"/tmp/browser_{session_name}_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Скриншот: {screenshot_path}")
        
        print(f"\n📡 Редиректы/ответы ({len(responses)}):")
        for r in responses[:10]:
            print(r)
        if len(responses) > 10:
            print(f"  ... и ещё {len(responses) - 10}")
        
        browser.close()


def login_with_qr(url: str, session_name: str = "default"):
    """Открыть URL в headless режиме для QR-кода (VK auth)
    VK часто использует QR для авторизации - покажем QR"""
    from playwright.sync_api import sync_playwright
    
    session_path = get_session_path(session_name)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 800, "height": 800}
        )
        page = context.new_page()
        
        page.goto(url, timeout=45000, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Ищем QR-код на странице
        qr_images = page.query_selector_all("img[src*='qr'], img[alt*='QR'], img[src*='qrcode']")
        if qr_images:
            print(f"🔍 Найдено QR-кодов: {len(qr_images)}")
            for i, qr in enumerate(qr_images):
                src = qr.get_attribute("src") or ""
                print(f"  QR #{i}: {src[:100]}")
        
        # Сохраняем скриншот на случай QR
        screenshot_path = f"/tmp/browser_qr_{session_name}.png"
        page.screenshot(path=screenshot_path)
        print(f"\n📸 Скриншот сохранён (возможно с QR-кодом): {screenshot_path}")
        print(f"   Открой его и отсканируй QR/войди, потом нажми Enter...")
        
        input("⏸️ Нажми Enter после входа...")
        
        # Сохраняем куки после входа
        cookies = context.cookies()
        session_path.write_text(json.dumps(cookies, indent=2))
        print(f"✅ Сессия '{session_name}' сохранена! {len(cookies)} кук.")
        
        print(f"\n📍 Текущий URL: {page.url[:150]}")
        body = page.inner_text("body")
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        print(f"\n📄 Страница входа:")
        for line in lines[:30]:
            print(f"  {line[:200]}")
        
        browser.close()


def list_sessions():
    """Показать все сохранённые сессии"""
    sessions = list(SESSIONS_DIR.glob("*.json"))
    if not sessions:
        print("Нет сохранённых сессий.")
        return
    
    print(f"Сохранённые сессии ({len(sessions)}):")
    for s in sessions:
        size = len(json.loads(s.read_text()))
        modified = time.ctime(s.stat().st_mtime)
        print(f"  {s.stem:20s} — {size} кук, изменена {modified}")


def delete_session(name: str):
    """Удалить сессию"""
    session_path = get_session_path(name)
    if session_path.exists():
        session_path.unlink()
        print(f"🗑️ Сессия '{name}' удалена.")
    else:
        print(f"❌ Сессия '{name}' не найдена.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "open":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        name = None
        screenshot = False
        for i, arg in enumerate(sys.argv):
            if arg == "--name" and i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
            if arg == "--screenshot":
                screenshot = True
        if not url:
            print("❌ Укажи URL: python3 session_browser.py open <URL>")
            sys.exit(1)
        open_url(url, name or "default", screenshot)
    
    elif command == "login":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        name = sys.argv[3] if len(sys.argv) > 3 else None
        if not url:
            print("❌ Укажи URL: python3 session_browser.py login <URL> [--name vk]")
            sys.exit(1)
        open_url(url, name or "default")
    
    elif command == "qr":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        name = None
        for i, arg in enumerate(sys.argv):
            if arg == "--name" and i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
        if not url:
            print("❌ Укажи URL: python3 session_browser.py qr <URL>")
            sys.exit(1)
        login_with_qr(url, name or "default")
    
    elif command == "list":
        list_sessions()
    
    elif command == "delete":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        if not name:
            print("❌ Укажи имя: python3 session_browser.py delete <name>")
            sys.exit(1)
        delete_session(name)
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        print(__doc__)
