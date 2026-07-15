# Tavily search failure and fallback strategies

**Дата:** 12.07.2026
**Ошибка:** Tavily возвращает 432 при поиске — «This request exceeds your plan's set usage limit»
**Диагностика:** `curl -s "https://api.tavily.com/search" -H "Content-Type: application/json" -d '{"query":"test","api_key":"$KEY"}'` → HTTP 432

## Причина

Dev-план Tavily (ключ `tvly-dev-...`) исчерпал лимит запросов. Ключ хранится в `/opt/zinaida/sandbox/configs/api_keys.json` в секции `tavily`.

## Fallback стратегии (когда Tavily не работает)

1. **DuckDuckGo через библиотеку ddgs:** `pip install ddgs` (уже установлен). Использовать через `from duckduckgo_search import DDGS` — бесплатно, без ключа.
2. **browser_navigate на duckduckgo.com** — открыть `https://duckduckgo.com/?q=...` через браузер
3. **VC.ru** через browser — открыть `https://vc.ru/`
4. **Готовые результаты** — в `/opt/zinaida/sandbox/deep_research/` лежат 20+ завершённых исследований. Проверить через `ls -lt` и `research_history.json`.
5. **deep_research_orchestrator.py** — сам использует Mistral/GitHub/Ollama (не Tavily) для анализа. Tavily нужен только как внешний поиск. Если падает только Tavily, остальное может работать.

## Когда исправлять

Чтобы Tavily снова заработал:
1. Купить новый план или получить новый dev-ключ
2. Вписать в `/opt/zinaida/sandbox/configs/api_keys.json` → `tavily: "новый_ключ"`
3. Перезапустить сервис: `systemctl restart zina2-router-8005.service`
