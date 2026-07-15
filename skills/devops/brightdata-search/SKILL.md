---
name: brightdata-search
description: "Поиск в интернете через BrightData SERP API. Бесплатно 5000 кредитов/мес, обновление 13 числа. Каскад: BrightData → DuckDuckGo → Server. Замена Tavily."
version: 1.2.0
author: Zinaida
---

# BrightData Search

## Когда использовать
Любой поиск в интернете для агентов, deep research, проверки фактов, поиска авторов, статей, источников.

## Скрипт
`/opt/zinaida/scripts/web_search_brightdata.py`

## Каскадный поиск (рекомендуется)
Все агенты используют каскад: **BrightData → DuckDuckGo → поиск по серверу**
Реализован в `cascade_search()` в `deep_research.py`.

Если BrightData упал (ошибка/таймаут) — автоматически пробует DuckDuckGo.
Если DuckDuckGo упал — поиск по локальным файлам сервера.
Если всё упало — возвращает пустой результат.

**Обновление кредитов:** 13 числа каждого месяца (5000 шт).
Подробнее: `references/pricing-renewal.md`

## Использование

### Прямой поиск через BrightData
```bash
python3 /opt/zinaida/scripts/web_search_brightdata.py "запрос" --limit 5
```

### Извлечение страницы
```bash
python3 /opt/zinaida/scripts/web_search_brightdata.py --extract "https://example.com"
```

## Из Python
```python
import subprocess, json
result = subprocess.run(
    ["python3", "/opt/zinaida/scripts/web_search_brightdata.py", "мой запрос", "--limit", "3"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
for r in data.get("results", []):
    print(r["title"], r["link"])
```

## Где используется
- deep_research.py — Раунд 1-3 через web_search()
- web_search_brightdata.py — прямой вызов
- Все роутеры (8002, 8003, 8005) — через RAG/усилители

## API ключ
Хранится в .env как BRIGHTDATA_KEY.
Пути: /root/.hermes/.env, /opt/zinaida/.env, /opt/zinaida/meta_agent/.env

## Лимиты
- Бесплатно: 5000 кредитов/мес
- 1 поиск = ~1-10 кредитов
- $5 добавлено на счёт (бесплатно)

## 🚨 ПИТФОЛЛ: «ЗАБЫЛ ПРО BRIGHTDATA»
**Дата:** 13.07.2026
**Ситуация:** При чистке MEMORY.md удалила запись про BrightData. Через час — пыталась чинить поиск через Google API (мёртвый) и ddgs, хотя BrightData работал и был основным.
**Причина:** BrightData был только в MEMORY.md. При чистке — исчез из памяти.
**Фикс:** 
1. Информация о BrightData должна быть в 13 точках: MEMORY.md, USER.md, Mem0, fact_store, SOUL.md, AGENTS.md, роутеры, bot.py
2. Если удаляешь из MEMORY.md — проверь что это есть в других местах
3. При любом вопросе «поиск/интернет» — сначала проверь BrightData, а не ddgs/Tavily

## Связь с другими навыками
- system-guarantee-protocol — протокол полного внедрения информации во все точки
- zinaida-tech-protocol — общий стек технологий (Context Engine, MOA, роутеры)
