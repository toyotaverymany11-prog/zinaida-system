# PLAYWRIGHT — ЖЕЛЕЗНЫЙ ИНСТРУМЕНТ ДЛЯ SPA/JS-САЙТОВ
**Дата добавления:** 18.07.2026
**Версия:** Playwright v1.61.0 | Chromium headless shell 1228

## Назначение
Чтение HTML-кода с SPA/JavaScript-сайтов, которые не отдают контент через curl (VK, id.vk.com, dev.vk.com и любые другие JS-сайты).

## Почему не curl?
Curl не исполняет JavaScript. SPA-сайты (React, Vue, Angular) рендерят контент через JS. Playwright запускает полноценный браузер Chromium headless, исполняет JS и возвращает готовый HTML.

## Установка
```bash
pip install playwright
python3 -m playwright install chromium-headless-shell
```

## Браузер
`/root/.cache/ms-playwright/chromium_headless_shell-1228/`

## Базовая команда
```python
python3 -c "
from playwright.sync_api import sync_playwright;
p = sync_playwright().start();
b = p.chromium.launch(headless=True);
page = b.new_page();
page.goto('URL');
print(page.content());
b.close();
p.stop()
"
```

## Применение
- VK API панели (id.vk.com, dev.vk.com)
- Любые SPA-сайты
- Сайты с JS-рендерингом контента
