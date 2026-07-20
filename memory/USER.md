# Пользовательская память (USER.md)

## 🚨 ЖЕЛЕЗНЫЙ ИНСТРУМЕНТ: PLAYWRIGHT (ДОБАВЛЕНО 18.07.2026)
Playwright v1.61.0 с Chromium headless shell 1228 установлен на сервере.
- Использовать ДЛЯ ЛЮБЫХ SPA/JS-сайтов (VK, id.vk.com, dev.vk.com)
- НЕ использовать curl для SPA — Playwright рендерит JavaScript
- Браузер: /root/.cache/ms-playwright/chromium_headless_shell-1228/
- Команда: python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(headless=True); page = b.new_page(); page.goto('URL'); print(page.content()); b.close(); p.stop()"
