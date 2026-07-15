# Pre-Flight Diagnostics: Zinaida Content Factory

Перед запуском любой генерации контента — проверь, что система в рабочем состоянии.

## Быстрая проверка (30 секунд)

```bash
# 0. HANDOVER и слепок — прочитать ДО начала работы
cat /opt/zinaida/HANDOVER_TO_NEW_CHAT.md 2>/dev/null || echo "HANDOVER не найден — читай SYSTEM_SNAPSHOT"
head -100 /opt/zinaida/memory/SYSTEM_SNAPSHOT.md 2>/dev/null | grep -E "(^#|^- |АКТИВ|СТАТУС)"

# 1. Живой слепок системы — приборная панель
python3 /opt/zinaida/sandbox/unified_diagnostic.py --text

# 2. Роутер жив?
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/v1/models

# 3. Базы данных на месте?
ls -la /opt/zinaida/memory/smm_rag.db /opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db
```

## Что проверять

### 1. Роутер (zinaida-openai-proxy / Router v4.0)
- Порт 8002 должен отвечать
- Если не отвечает: `systemctl restart zinaida-router` или `python3 /opt/zinaida/meta_agent/zinaida_openai_proxy.py &`
- Проверка `/v1/health` может возвращать 404 — это нормально для некоторых версий роутера. Ориентируйся на `/v1/models`.
- **Логи роутера:** скрипт использует `logging.basicConfig(level=logging.INFO, ...)` без `filename` — логи идут в **stderr**. systemd по умолчанию ловит только stdout.
  - **Что работает:** `systemctl status zinaida-router` — показывает статус демона.
  - **Путь `/opt/zinaida/logs/router.log` НЕ СУЩЕСТВУЕТ** — роутер НЕ пишет в файл. Не пытайся читать оттуда.
  - **Провайдеры (Router v4.0, состояние на 08.07.2026):** 5 из 7 alive.
    - **Alive:** deepseek_flash, deepseek_pro, github, mistral, zhipu
    - **Dead:** openrouter (403), gigachat (402)
    - **Квирк deepseek-reasoner (deepseek_pro):** при `stream=False` возвращает пустой контент (вероятно, не фильтруются thinking/reasoning-токены). Если нужен deepseek_reasoner — используй `stream=True` или фильтруй ответ после получения.
  - **GigaChat специфика:** 2 API-ключа с авто-ротацией при исчерпании лимита. Токен живёт 30 минут — нужна схема авторизации с периодическим обновлением. Текстовые запросы через GigaChat возможно бесплатные (платные только картинки).

### 2. Поиск (web search) — проверка доступности

**Частая проблема:** поиск не работает, хотя API-ключи были предоставлены. Перед поиском — проверь, что инструмент сконфигурирован.

```bash
# 1. Проверить, что web_search в принципе настроена (Hermes tools)
cat ~/.hermes/config.yaml | grep -A 10 -i search 2>/dev/null || echo "config.yaml не найден"

# 2. Проверить переменные окружения для поиска
env | grep -iE 'TAVILY|SERP|BRAVE|SEARCH|BING|GOOGLE' || echo "ключи поиска не найдены в env"

# 3. Проверить .env файлы
cd /opt/zinaida && grep -iE 'TAVILY|SERP|BRAVE|SEARCH|BING|GOOGLE' .env 2>/dev/null || echo "не найдено в .env"
```

**Если ключи не найдены (env пуст):**
1. Выполни `session_search("поиск ключи API")` — пользователь мог дать ключи в предыдущих сессиях и они остались в истории чата
2. Спроси у оператора: «Какие ключи для поиска ты давал? Я вижу, что инструмент поиска не сконфигурирован»
3. После получения ключей — установи через `export SEARCH_API_KEY=...` или запиши в `.env` файл

**Fallback при недоступности web_search:**
- Используй `web_extract()` с прямыми URL (если знаешь, где искать)
- Используй `browser_navigate()` для поиска через браузер

### 3. Базы данных
- `smm_rag.db` — должна быть >0 записей (сейчас ~3975)
- `phases.db` — 41 фаза
- `content_rotation.db` — должна существовать
- `analytics.db` — метрики

### 4. Директории очереди
```bash
ls /opt/zinaida/SmmFabrika/queue/
```
Должны быть папки платформ: VK, Instagram, Dzen, Telegram, Odnoklassniki, Pinterest, MessengerMax, YandexMessenger

### 5. Сервисы
- `ira-bot` — active
- `caddy` — active
- Проверка: `systemctl status ira-bot caddy`

## Если что-то не так

| Проблема | Действие |
|----------|----------|
| Роутер не отвечает | Запустить: `python3 /opt/zinaida/meta_agent/zinaida_openai_proxy.py &` |
| База smm_rag.db пуста | Переиндексировать через скрипт RAG |
| Нет папки платформы | Создать: `mkdir -p /opt/zinaida/SmmFabrika/queue/{VK,Instagram,Dzen,Telegram,Odnoklassniki,Pinterest,MessengerMax,YandexMessenger}` |
| OneDrive не смонтирован (для картинок) | `rclone mount onedrive: /opt/zinaida/inbox/Контент --daemon` |
| Поиск (web_search) не работает | См. раздел 2 выше. Проверить `env`, `.env`, `session_search()` |

### 6. ALL providers unavailable (полный отказ — транзиентный)

**Важно:** Если роутер жив (порт 8002 отвечает), а провайдеры **все** упали — это **транзиентный (временный) отказ**. Не спеши чинить, не перезапускай роутер, не лезь в код. Просто подожди.

**Установленный паттерн:** провайдеры (особенно DeepSeek, Mistral, GitHub) периодически ложатся на 30–120 секунд, а потом восстанавливаются сами. Роутер их не кеширует — каждый новый запрос пробует заново.

**Протокол диагностики за 15 секунд:**

```bash
# 1. Роутер жив? (должен быть 200)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8002/v1/models

# 2. Какие провайдеры известны роутеру?
curl -s http://127.0.0.1:8002/v1/models | python3 -c "import sys,json; models=json.load(sys.stdin); print(f'{len(models[\"data\"])} моделей'); [print(f'  {m[\"id\"]}') for m in models['data']]" 2>/dev/null || echo "роутер не ответил"

# 3. Тест completions эндпоинта (дышит ли?)
curl -s -X POST http://127.0.0.1:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"1+1"}],"max_tokens":5}' \
  -w "\nHTTP_CODE:%{http_code}" 2>/dev/null | tail -5
```

**Протокол действий:**

1. **Шаг 1 — Проверь** роутер (`/v1/models`). Если отвечает — роутер жив, проблема только в апстримах.
2. **Шаг 2 — Скажи оператору честно:** «Роутер жив, провайдеры временно полегли. Обычно восстанавливаются за 30-120 секунд. Предлагаю подождать минуту и повторить.»
3. **Шаг 3 — Подожди 60 секунд**, затем повтори запрос:
   ```bash
   sleep 60 && curl -s -X POST http://127.0.0.1:8002/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"тест"}],"max_tokens":10}' \
     -w "\nHTTP_CODE:%{http_code}" | tail -3
   ```
4. **Шаг 4 — Если после 60 секунд всё ещё не работает**, покажи отчёт: роутер жив, модель N отвечает HTTP X. Предложи оператору альтернативы:
   - Перезапуск роутера: `systemctl restart zinaida-router`
   - Fallback на другую модель / провайдера (если хоть один доступен)
   - Работать позже

**Запрещено:**
- Сразу перезапускать роутер при первом «все провайдеры упали» — транзиентный отказ проходит сам
- Лечить код роутера в разгар отказа — после восстановления он работает нормально
- Постить в чат сырые дампы логов (systemctl status, journalctl) без фильтрации — это пугает оператора

**Как сообщать оператору:**
```
[ЗИНАИДА] Роутер жив, но провайдеры временно не отвечают (все).
Такое бывает — проходит за 1-2 минуты. Предлагаю подождать и попробовать снова.
Если не восстановится — перезапущу роутер или переключу на резервную модель.
```

### 7. Частичный отказ провайдеров (partial provider failure)

### 8. Hermes Studio модельный листинг

Если работаешь через Hermes Studio (UI) и не видишь модели Zinaida-Router видит дубликаты:

```bash
# Быстрая проверка: что отдаёт роутер
curl -s http://127.0.0.1:8002/v1/models | python3 -m json.tool 2>/dev/null | grep '"id"'

# Сколько раз Zinaida-Router упомянут в конфиге Hermes
grep -c "Zinaida" ~/.hermes/config.yaml 2>/dev/null

# Если дубли — см. references/hermes-studio-integration.md
```

**Типовая причина дубликатов:** провайдер Zinaida-Router указан в конфиге несколько раз (в разных профилях).
**Решение:** удалить дублирующихся провайдеров через Settings → Providers в Studio.

**Типовая причина «модели не видны»:** модели не перечислены явно в секции `providers[].models` конфига Hermes.
   - GPT/Claude/YandexGPT — обычно стабильны
   - DeepSeek — дешёвый, но может быть перегружен
   - GigaChat — падает при проблемах с Сбером
   - Gemini — хороший backup

3. Если доступна хотя бы одна модель — продолжай работу. **Не останавливай конвейер.**

4. В ответе оператору укажи:
   - Какие провайдеры работают
   - Какие провайдеры отказали (с кодом ошибки)
   - Какая модель использовалась для генерации

5. Пример отчёта:
   > Роутер жив. DeepSeek и GigaChat временно недоступны (502). Работаю через gpt (OpenAI GPT-4o). Пост сгенерирован, сохранён в очередь.

**Запрещено:**
- Сдаваться и сообщать «ничего не работает» если часть провайдеров жива
- Делать 3+ ретраев на упавший провайдер — одного достаточно
- Тратить время на диагностику отказавшего провайдера вместо переключения на рабочий

## После генерации — валидация

Проверить, что пост сохранён:
```bash
ls -la /opt/zinaida/SmmFabrika/queue/<Platform>/<YYYY-MM-DD>/
```

Проверить статус роутера (если нужна дебаг-инфа):
```bash
systemctl status zinaida-router
```
Логи роутера идут в stderr, не в файл. `/opt/zinaida/logs/router.log` не существует.
