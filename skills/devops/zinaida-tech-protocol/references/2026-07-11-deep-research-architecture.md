# Система Deep Research — техническая архитектура (11.07.2026)

## Состав агентов и роли

| Агент | Модель | Роль | Поиск | Fallback | Стоимость |
|-------|--------|------|-------|----------|-----------|
| Mistral | mistral-small-latest | tavily_broad (широкий обзор) | Tavily API | - | Бесплатно |
| Mistral2 | mistral-small-latest | duckduckgo (второй поисковик) | DuckDuckGo (ddgs) | - | Бесплатно |
| GitHub | gpt-4o-mini | server_search (поиск по серверу) | grep + SQLite | Mistral | Бесплатно |
| Ollama | gemma3:27b | tavily_narrow (цифры/даты) | Tavily | - | Условно |
| DeepSeek (Pro) | deepseek-chat (V3) | Раунд 4 синтез + Раунд 2 оценка | — | — | Платно ($0.27/1M in) |

## Ключевые файлы

### Скрипты
- `/opt/zinaida/scripts/deep_research.py` — ядро (4 раунда, параллельный сбор)
- `/opt/zinaida/scripts/deep_research_orchestrator.py` — интерфейс запуска
- `/opt/zinaida/scripts/openrouter_monitor.py` — монитор OpenRouter (актуален при смене IP)

### Конфигурация
- **DuckDuckGo:** установлен `pip install ddgs`. Импорт: `from ddgs import DDGS`. Без ключа.
- **Tavily:** ключ в `/root/.hermes/.env` (TAVILY_API_KEY)
- **Mistral:** 3 ключа в `/opt/zinaida/config/secrets.env`
- **GitHub:** 1 рабочий ключ GITHUB_TOKEN в `/opt/zinaida/config/secrets.env`. Второй (GREG_GITHUB_TOKEN) мёртв (401).
- **DeepSeek:** DEEPSEEK_API_KEY в `/opt/zinaida/.env`
- **Ollama:** 3 ключа в `/opt/zinaida/config/secrets.env`, работает нестабильно

### HTML визуализация
- splash: https://zinadchdp.duckdns.org/research/deep_research_splash.html
- report.html: в папке результата, доступен через Caddy по HTTPS
- Caddy route: `/research/*` → `/opt/zinaida/`

### Аудитория
- Запуск: `python3 /opt/zinaida/scripts/deep_research.py "тема"`
- Результат: `/opt/zinaida/sandbox/deep_research/{timestamp}_{topic}/`
