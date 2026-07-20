# AGENTS.md — Железные правила для всех агентов

## 🔴 ПОИСК В ИНТЕРНЕТЕ (18.07.2026)
Два инструмента:
1. **BrightData** — приоритет №1. Ключ `929dbdc5-0160-4acd-9fe3-ca85d604a3fe` в `/opt/zinaida/.env` и `/root/.hermes/.env`. **Bearer** токен. Вызов: `python3 /opt/zinaida/scripts/web_search_brightdata.py "запрос" --limit N`
2. **DuckDuckGo** — built-in web.backend в Hermes. Без ключа, бесплатно. Fallback если BrightData не отвечает.

При любом запросе «найди/поищи/найти/проверь/нагугли» — сначала BrightData, потом DuckDuckGo.
Не пытаться чинить — если BrightData таймаутит, сразу DuckDuckGo.

## 🔴 PLAYWRIGHT — ЧТЕНИЕ SPA/JS-САЙТОВ (ДОБАВЛЕНО 18.07.2026)
Playwright v1.61.0 с Chromium headless shell 1228.
Использовать для получения HTML с любых SPA/JS-сайтов (VK, id.vk.com, dev.vk.com). НЕ curl — Playwright рендерит JS.
Команда: `python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(headless=True); page = b.new_page(); page.goto('URL'); print(page.content()); b.close(); p.stop()"`
Браузер: /root/.cache/ms-playwright/chromium_headless_shell-1228/

## 🔴 ПРАВИЛО АВТОМАТИЧЕСКОГО ВНЕДРЕНИЯ НОВЫХ ИНСТРУМЕНТОВ (ДОБАВЛЕНО 18.07.2026)
Любой агент, нашедший/установивший новый инструмент, который:
1. ✅ Реально работает
2. ✅ Решает проблему
3. ✅ Будет нужен в будущем
→ ОБЯЗАН самостоятельно внедрить его во все точки: MEMORY.md, USER.md, Mem0, SOUL.md, AGENTS.md, fact_store, updates_log, навык. Не ждать команды.

## 🔴 СЕССИОННЫЙ БРАУЗЕР
Есть `session_browser.py` и `vk_session.py` в `/opt/zinaida/scripts/`. Для чтения VK/dev.vk.com с авторизацией. Куки в `/opt/zinaida/browser_sessions/`. Навык: `session-browser`.
Для любого SPA/JS-сайта — использовать session_browser, НЕ curl.
Не говорить «провайдер мёртв» без реальной проверки: `python3 /opt/zinaida/scripts/provider_truth_check.py <provider>`. DeepSeek жив (ключ sk-0d4b7c87), BrightData жив (ключ 929dbdc5).
