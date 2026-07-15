# Deep Research Swarm — Implementation Details (10.07.2026)

## Скрипт
- **Путь:** `/opt/zinaida/scripts/deep_research.py` (940 строк, протестирован)
- **Зависимости:** `requests`, `python-dotenv` (опционально — свой парсер .env)
- **Чтение темы:** stdin
- **Параллельность:** `concurrent.futures.ThreadPoolExecutor`, timeout 30s

## API Endpoints — точные адреса

### Tavily
- URL: `https://api.tavily.com/search`
- Ключ: `TAVILY_API_KEY` в `/root/.hermes/.env`
- Формат: POST, JSON `{"api_key": "...", "query": "test", "search_depth": "advanced", "include_raw_content": true, "max_results": 5}`
- Статус: Работает (200)

### GigaChat (падает!)
- OAuth: `POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
  - Заголовки: `Authorization: Basic {GIGACHAT_CLIENT_SECRET}`, `Content-Type: application/x-www-form-urlencoded`, `RqUID: {GIGACHAT_CLIENT_ID}`
  - Body: `scope=GIGACHAT_API_PERS`
  - verify=False (самоподписной сертификат)
  - Статус: **400** — OAuth не проходит
- Chat: `POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions`
  - Заголовки: `Authorization: Bearer {access_token}`, `Content-Type: application/json`
  - Модель: `GigaChat`
  - verify=False

### Mistral
- URL: `POST https://api.mistral.ai/v1/chat/completions`
- Ключ: `MISTRAL_API_KEY` (основной), `MISTRAL_API_KEY_2`, `MISTRAL_API_KEY_3`
- Модель: `mistral-small-latest` (быстрее) или `mistral-large-latest`
- Статус: Работает (200, время ~1-3s)

### GitHub Models
- URL: `POST https://models.inference.ai.azure.com/chat/completions`
- Ключ: `GITHUB_TOKEN` (из `/opt/zinaida/config/secrets.env`)
- Модель: `gpt-4o-mini`
- Статус: Работает (200, время ~10s через proxy)

### Ollama
- URL: `POST https://ollama.com/v1/chat/completions`
- Ключи: `OLLAMA_API_KEY_1`, `OLLAMA_API_KEY_2`, `OLLAMA_API_KEY_3`
- Модель: `gemma3:27b`
- Статус: Работает (время 5-15s локально)

### DeepSeek Pro (финальный судья)
- URL: `POST https://api.deepseek.com/chat/completions`
- Ключ: `DEEPSEEK_API_KEY` (из `/opt/zinaida/.env`)
- Модель: `deepseek-chat` (не deepseek-reasoner для speed)
- Статус: Работает (200, время ~2-5s)

## Тестовый прогон
- **Дата:** 10.07.2026, ~21:00
- **Тема:** «Почему мужчины уходят после 3 лет отношений»
- **Результат:** 3/4 агента отработали (GigaChat упал с 400)
- **DeepSeek синтез:** 79 строк, структурированный отчёт
- **Вывод скрипта:** `/opt/zinaida/sandbox/deep_research/20260710_210015_почему_мужчины_уходят_после_3_лет_отношений/final_report.md`

## Рекомендации по усилению
1. Починить GigaChat — обновить OAuth или заменить на OpenRouter (ключ `OPENROUTER_KEY` есть)
2. Подключить Brave Search API — 2000 запросов/мес бесплатно
3. Прикрутить триггер «глубокое исследование: тема» к запуску скрипта
4. Сделать output не только файлом, но и в чат Hermes Studio
