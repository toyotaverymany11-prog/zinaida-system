# Hermes Studio: обновление и диагностика версий

## Как проверить текущую версию
```bash
npm list -g hermes-web-ui           # установленная версия
systemctl status hermes-web-ui       # запущенная версия (в Description)
curl -s http://127.0.0.1:8648/       # что отвечает (200 = жив)
```

## Как обновить
```bash
npm update -g hermes-web-ui          # обновить пакет
systemctl restart hermes-web-ui      # перезапустить сервис
```

## Типовая проблема: версия не обновляется
**Симптом:** npm показывает новую версию, но интерфейс старый, кнопка микрофона не появилась.

**Корень:** В системе может быть ДВЕ установки:
- `/usr/lib/node_modules/hermes-web-ui/` — старая (через apt/system)
- `/usr/local/lib/node_modules/hermes-web-ui/` — новая (через npm -g)

Проверить:
```bash
cat /usr/lib/node_modules/hermes-web-ui/package.json | grep version
cat /usr/local/lib/node_modules/hermes-web-ui/package.json | grep version
file /usr/bin/hermes-web-ui  # symlink куда ведёт?
```

**Фикс:** Перенаправить symlink на новую версию:
```bash
ln -sf /usr/local/lib/node_modules/hermes-web-ui/bin/hermes-web-ui.mjs /usr/bin/hermes-web-ui
systemctl restart hermes-web-ui
```

## Кэш браузера (service worker)
**Симптом:** Новая версия установлена, но интерфейс не изменился.

**Фикс (на iPad Safari):**
- Закрыть все вкладки с Hermes Studio
- Settings → Safari → Clear History and Website Data
- Или: зажать кнопку обновления → «Удалить кэш и перезагрузить»

Известный баг: github.com/nesquena/hermes-webui/issues/1507 — stale CSS после container update.

## Voice Dialogue (микрофон в чате)
- Появился в v0.6.27+
- Включается в Settings → Voice
- STT: Browser (встроенное распознавание браузера, без ключей)
- TTS: Browser или Edge TTS
- Кнопка микрофона 🎤 — справа внизу поля ввода
- Режим: полудуплекс (запись → транскрибация → редактирование → отправка)

## Что НЕ делать
- Не использовать `npm update` без проверки версии после
- Не перезапускать сервис не проверив symlink
- Не отправлять Олегу ссылку на Hermes Studio не проверив что она открывается
