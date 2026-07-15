---
name: hermes-studio-diagnostics
description: Диагностика ошибок Hermes Studio (Web UI) — 500, краши, обрывы сессий, таймауты. Последовательный протокол поиска корневой причины.
---

# Hermes Studio Diagnostics

Диагностика проблем с Hermes Studio (веб-интерфейс Hermes Agent).

## Быстрая проверка

```bash
# Статус сервиса
systemctl status hermes-web-ui --no-pager -l

# Версия установленного пакета
npm list -g hermes-web-ui 2>/dev/null || cat /usr/lib/node_modules/hermes-web-ui/package.json | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])"

# Последняя доступная версия
npm view hermes-web-ui version 2>/dev/null || echo "check npm"

# Версия в systemd (может отличаться от npm!)
grep Description /etc/systemd/system/hermes-web-ui.service
```

## Обновление Hermes Studio

**Сигнал:** Олег говорит «обнови Hermes» или версия отстаёт от последней.

**Процедура:**
```bash
npm update -g hermes-web-ui                     # шаг 1
sed -i 's/Description=Hermes Web UI v.*/Description=Hermes Web UI v<новая_версия>/' /etc/systemd/system/hermes-web-ui.service
systemctl daemon-reload                          # шаг 2
systemctl restart hermes-web-ui                  # шаг 3
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8648/  # шаг 4: должен быть 200
```

**Важно:** После обновления записать версию в built-in memory, чтоб не терять.
Формат: «Hermes Studio обновлён до vX.Y.Z (дата). Пакет: npm hermes-web-ui@X.Y.Z.»

## Голосовой ввод/вывод (Voice Dialogue)

Hermes Studio v0.6.27+ имеет **встроенный голосовой ввод/вывод** прямо в чате.
Документация: https://github.com/EKKOLearnAI/hermes-studio/blob/main/docs/voice-dialogue.md

**Что есть:**
- Кнопка микрофона 🎤 в поле ввода сообщения
- STT: браузерный SpeechRecognition (без ключей) или серверный провайдер
- TTS: браузерный SpeechSynthesis или серверный провайдер
- Barge-in: если агент говорит, а пользователь начинает говорить — агент замолкает
- Настройки: Settings → Voice (STT/TTS провайдеры)

**Если кнопки микрофона нет:**
1. Обновить Hermes Studio до последней версии
2. Проверить настройки Settings → Voice
3. Сделать Ctrl+Shift+R (hard refresh)

**Что НЕ реализовано (пока):**
- Wake-word (always-on listening)
- Full-duplex (одновременный говор/слушание)
- Телефония

## Трассировка происхождения сессии (кто создал этот чат)

**Симптом:** Пользователь видит сессию, которую он не создавал. Первое сообщение — «Say hello in 3 words» или другое тестовое.

**Корень:** Hermes Agent может авто-создавать сессии при переключении модели (`switch_model`) или после восстановления MCP-соединений. Эти сессии идут от `MainThread` с `platform=cli` и `history=0` — не от пользователя.

**Диагностика:** смотреть `references/session-origin-tracing.md` — полный протокол с 5 шагами и 4 типовыми сценариями.

**Ключевые признаки авто-сессии:**
- `platform=cli`, `thread=MainThread`, `history=0`
- В логах перед созданием: `switch_model` или `agent_init`
- Пользователь не был залогинен в момент создания (проверить через `last`)

## Журналы для просмотра

| Источник | Путь | Что искать |
|----------|------|------------|
| systemd journal | `journalctl -u hermes-web-ui -n 200 --no-pager` | `error`, `500`, `crash`, `exception`, `timeout`, `unhandled` |
| server.log | `/root/.hermes-web-ui/logs/server.log` | structured JSON-логи с `level>=40` (warn/error) |
| server.log (старый) | `/root/.hermes-web-ui/server.log` | plain-text логи до переезда на structured |
| bridge.log | `/root/.hermes-web-ui/logs/bridge.log` | ошибки agent-bridge |
| gateway journal | `journalctl -u hermes-gateway -n 100 --no-pager` | ошибки gateway |

## Типовые проблемы

### 1. Ошибка 500 при загрузке файлов / обрывы сессии

**Симптомы:** Пользователь загружает файл (docx, изображение), UI падает с 500, агент перестаёт отвечать, в логах сервера — **нет** явных ошибок.

**Корень:** Версия установленного пакета (npm) не совпадает с версией кэшированного браузером клиентского JS. Установлен новый пакет (`npm update -g hermes-web-ui`), но браузер отдаёт старый JS из кэша → несовместимость API → 500.

**Фикс:**
1. `Ctrl+Shift+R` (жёсткая перезагрузка без кэша) в браузере
2. Если не помогло — очистить кэш браузера полностью
3. В крайнем случае — открыть вкладку в режиме инкогнито

**Профилактика:** После `npm update -g hermes-web-ui && systemctl restart hermes-web-ui` обязательно делать hard refresh.

### 2. Таймаут сервиса (Failed with result 'timeout')

**Симптомы:** `systemctl status hermes-web-ui` показывает fail с таймаутом.

**Корень:** Долгая операция (загрузка большого файла, парсинг docx, LLM-запрос через bridge) не уложилась в лимит systemd `TimeoutStopSec` или `TimeoutStartSec`.

**Диагностика:**
```bash
journalctl -u hermes-web-ui --no-pager | grep -i timeout
```

**Фикс:** Увеличить таймауты в `/etc/systemd/system/hermes-web-ui.service`, если проблема повторяется.

### 3. Bridge worker упал

**Симптомы:** Агент не отвечает, в server.log: `[agent-bridge] exited code=... signal=...`.

**Диагностика:** `/root/.hermes-web-ui/logs/bridge.log`

**Фикс:** `systemctl restart hermes-web-ui` — bridge перезапустится автоматически.

### 4. Ошибка 500 с Python-текстом (ошибка роутера, не UI)

**Симптомы:** В браузере HTTP 500 с телом вида `{'error': "'list' object has no attribute 'strip'"}`.
В логах Hermes Studio (`server.log`, `journalctl`) — **нет** ошибок, сервис жив.

### 🧹 Отображение tool output в чате (технический мусор между сообщениями)

**Симптомы:** В чате Hermes Studio (или Telegram) отображаются результаты работы инструментов — terminal, read_file, patch, curl и т.д. Пользователь видит техническую простыню вместо чистого диалога.

**Причина:** В config.yaml стоит `display.tool_progress: all` (значение по умолчанию).

**Решение:**
```bash
hermes config set display.tool_progress off
```

После этого в чате останутся только текстовые ответы агента. Результаты инструментов скрываются.

**Дополнительно:**
- `display.compact: true` — ещё более компактный режим
- `tool_progress_command: false` — скрыть выполненные команды (не их результаты)

**Обоснование:** Документировано в Hermes Agent docs (`display.tool_progress: off | new | all | verbose`), подтверждено Reddit r/hermesagent.

**Корень:** Роутер (`zinaida_openai_proxy.py`, порт 8002) перехватывает все исключения в `route_chat()` 
и возвращает их как HTTP 500. Ошибка не в UI, а в Python-коде роутера.

**Диагностика:**
```bash
# Проверить лог роутера
journalctl -u zinaida-router --no-pager -n 50 | grep -i error

# Проверить что роутер отвечает
curl -s http://127.0.0.1:8002/health

# Повторить запрос напрямую к роутеру
curl -s -X POST http://127.0.0.1:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"тест"}],"max_tokens":10}'
```

**Типовая ошибка: `'list' object has no attribute 'strip'`**

Причина: клиент передаёт сообщение с `content` как список частей (мультимодальный запрос с файлом).
Функция `shrink_messages` раньше пропускала content-список, а `_gigachat_clean_messages`
вызывала `.strip()` на списке.

**Фикс:** в `/opt/zinaida/meta_agent/zinaida_openai_proxy.py` добавлена функция `_content_to_str()`,
которая превращает content (строка/список/None) в строку. Вызывается в начале `shrink_messages`.

После фикса — `systemctl restart zinaida-router`.

**Другие ошибки роутера:** см. `zinaida-operations` → раздел 8.5

### 5. Reasoning-блоки («Процесс размышления») в ответах

**Симптом:** В Web UI перед ответом показывается блок «Процесс размышления · N зн.» на английском с мыслями модели. Олег в ярости от этого.

**Причина:** Два независимых источника:
1. Hermes config `display.show_reasoning: true` — добавляет `💭 Reasoning:` блок
2. Модель DeepSeek возвращает `reasoning_content` в SSE-чанках — Web UI рисует как отдельный блок

**Фикс (оба уровня обязательны):**
```bash
# Уровень 1: Hermes config
sed -i 's/show_reasoning: true/show_reasoning: false/' /root/.hermes/config.yaml
systemctl restart hermes-gateway.service

# Уровень 2: Роутер — вырезает reasoning_content на лету
systemctl restart zinaida-router.service
```

**Проверка:** После перезагрузки сделать Ctrl+Shift+R (hard refresh) в браузере. Если чат уже начат — `/reset`.

## Полный чеклист при ошибке 500

1. `systemctl status hermes-web-ui` — сервис жив?
2. `journalctl -u hermes-web-ui --no-pager -n 50 | grep -iE \"500|error|crash\"` — есть записи?
3. Если логи UI чисты — ошибка в роутере: `curl -s http://127.0.0.1:8002/health` и `journalctl -u zinaida-router --no-pager -n 50 | grep -i error`
4. Если и там чисто — проверить gateway: `systemctl status hermes-gateway` и `journalctl -u hermes-gateway --no-pager -n 50`
5. `tail -100 /root/.hermes-web-ui/logs/server.log | python3 -c \"import sys,json; [print(l) for l in sys.stdin if 'level' in l and json.loads(l).get('level',0)>=40]\"` — warn/error в структурированных логах
6. Сверить версию пакета с последней: `npm view hermes-web-ui version`
7. Если версия отстаёт → `npm update -g hermes-web-ui && systemctl restart hermes-web-ui && Ctrl+Shift+R`

## Пути к файлам

- Сервис: `/etc/systemd/system/hermes-web-ui.service`
- Директория: `/root/.hermes-web-ui/`
- Логи: `/root/.hermes-web-ui/logs/server.log`, `/root/.hermes-web-ui/logs/bridge.log`
- Старые логи: `/root/.hermes-web-ui/server.log`
- Загрузки: `/root/.hermes-web-ui/upload/default/`
