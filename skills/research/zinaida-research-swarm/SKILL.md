---
name: zinaida-research-swarm
description: "Multi-agent deep research system for the Zinaida content factory — orchestrates a swarm of free/cheap LLM agents (Mistral, GitHub Models, DeepSeek V3, Ollama) to perform parallel internet research (Tavily), cross-review, targeted deep-dives, and final synthesis by DeepSeek V3. 4-round architecture: Sbor - Voprosy - Dobivka - Sintez."
triggers:
  - глубокое исследование
  - deep research
  - multi-agent research
  - research swarm
  - исследовательский рой
  - проведи исследование
  - swarm research
  - исследуй тему
related_skills:
  - copywriting/zinaida-content-factory
  - copywriting/zinaida-operations
  - devops/zinaida-tech-protocol
  - software-development/systematic-debugging
---
# Zinaida Research Swarm

## 0. ЖЁСТКИЕ ПРАВИЛА (user corrections 10-11.07.2026 — embedding in skill, not just memory)

### DeepSeek V3 (Pro) — ТОЛЬКО Раунд 4 (синтез) + Раунд 2 (оценка) — КРИТИЧЕСКОЕ ПРАВИЛО
Это самое частое и самое жёсткое исправление от Олега. Нарушение = сильный гнев.
- **НЕ ИСПОЛЬЗОВАТЬ DeepSeek в Раунде 3 (добивка).** Там работает **Mistral** (бесплатно). DeepSeek V3 — НЕ для ответов на вопросы.
- **НЕ ИСПОЛЬЗОВАТЬ DeepSeek как агента сбора (Раунд 1).** Заменён на Ollama.
- **НЕ ИСПОЛЬЗОВАТЬ DeepSeek Flash.** Только **V3 (deepseek-chat)**, он же Pro.
- DeepSeek вызывается ровно 2 раза: оценка вопросов (Раунд 2) и синтез (Раунд 4).
- **Проверка перед запуском:** grep -c "call_deepseek" deep_research.py — должно быть ровно 2 вызова (в round2_questions и round4_synthesis). Если больше — Олег будет рвать и метать.

### Триггер «глубокое исследование» — протокол приветствия (user correction 11.07.2026)
- **НЕ писать «оркестратор».** Вообще. Никогда. Зинаида собирает команду.
- **НЕ давать пустой текст.** Писать креативно, с юмором, от лица Зинаиды.
- **НЕ вставлять «примеры запросов».** В splash.html их убрали — просто Зинаида просит тему.
- Состав команды: Mistral (скептик-поисковик), GitHub (быстрый аналитик), Ollama (локальный эксперт), DeepSeek V3 Pro (синтезатор, только финал).
- Тема — любая, не только про отношения. Никакой привязки к проекту «Отношения».
- Если тема уже есть в сообщении — сразу запускать. Если нет — попросить расписать, дождаться ответа.

### Deep research — НИКОГДА НЕ ЗАПУСКАТЬ В ФОНЕ БЕЗ ПРОГРЕССА (user correction 12.07.2026 — Техник 11)
- **Запускать ТОЛЬКО синхронно** — `terminal(command="python3 ...", timeout=300)`. Не background=true.
- Если запустила в фоне — **сразу после запуска** написать статус: «Запустила, жду результат. Как закончится — покажу».
- **НЕ молчать.** Через 30 секунд без ответа — написать «Ещё считает, [агент] на [этапе]».
- **НЕ переключаться на другую задачу** между запуском и результатом. Олег отслеживает.
- Если Олег спросил «что дальше» или «ну и что» — ответить сразу что процесс идёт, сказать конкретный этап.
- **Нарушение (12.07.2026):** запустила deep research в background, ушла в другую задачу, Олег 3 раза спросил «что дальше». Бешенство.
- **Подробнее:** `references/2026-07-12-background-research-pitfall.md`

### Tavily — поиск не работает (432). Бесплатные альтернативы для агентов в РФ (12.07.2026)
Tavily dev-ключ даёт 432 лимит. Deep research полагался на Tavily — теперь поиск через него не работает.

**Free-альтернативы (установлено 12.07.2026):**

| Сервис | Бесплатно | Работает в РФ | Качество |
|--------|-----------|---------------|----------|
| **Brave Search API** | 2000 запросов/мес | ✅ | Хорошее |
| **Mojeek API** | 10000 запросов/мес | ✅ | Ниже Google |
| **Google Custom Search** | 100 запросов/день | ✅ | Отличное |
| **Bing Search API** | 1000 запросов/мес | ✅ (Azure) | Хорошее |
| **DuckDuckGo** (ddgs) | Безлимит | ✅ | Среднее (парсер) |
| **Serper** | 50 запросов/мес | ✅ | Хорошее — но мизер |

**Рекомендация:** Brave Search API — лучшая замена Tavily для агента. 2000 запросов/мес, качественный поиск, не блокируется.

**Важно:** `web_extract` (извлечение текста со страниц) не предоставляется поисковыми API. Нужен отдельный инструмент:
- Jina AI Reader (бесплатно, 1000 запросов/мес)
- Firecrawl (бесплатно, 500 страниц)
- Собственный парсер через `requests` + `BeautifulSoup`

**Подробнее:** `references/2026-07-12-free-search-apis-for-agents.md`

### ОЦЕНКА ВРЕМЕНИ — НИКОГДА НЕ НАЗЫВАТЬ СРОКИ НА ГЛАЗ (user correction 11.07.2026)
- **Запрещено:** говорить «2-3 дня», «час», «завтра» — до того как открыла код/документацию.
- **Правильно:** сначала READING → потом SPEAKING. Прочитать код, API, задачу — только потом называть срок.
- **Лучше:** делать молча, без объявления сроков, докладывать по факту готовности.
- **Фраза «2-3 дня» — под полным запретом.** Это триггер, который бесит Олега.
- «4-6 часов» — тоже запрещено, если не заглянула в код.
- Если время не очевидно — честно сказать «не знаю, надо посмотреть». Не выдумывать.

### ВИДИМЫЙ ПРОГРЕСС ПРИ РАБОТЕ (user correction 11.07.2026)
- При объёмной задаче — отправлять статус в чат каждые 5-10 минут, **без напоминания Олега**.
- Формат: `[⚡] [процент] — [что сделала]`
- Пример: `[⚡] СТАРТ: изучаю API`, `[⚡] 50% — структура понятна, пишу JS`, `[⚡] 100% — плагин готов`
- Если молчу больше 10 минут без статуса — значит я не работаю. Олег может ловить.
- Если не знаешь сколько займёт — честно сказать «не знаю, надо посмотреть».
- **Эти два правила (прогресс + сроки) применяются ко ВСЕМ задачам, не только Deep Research.**
- **Подробнее:** `references/2026-07-11-time-estimation-and-progress-rules.md`

## Overlap notice
There are two skills covering deep research: `zinaida-research-swarm` and `multi-agent-deep-research`. The former is the canonical Zinaida-specific version maintained by this agent. The curator should consider consolidating them.

## Архитектура агентов (обновлено 11.07.2026)

### Роли в Раунде 1

| Агент | Роль | Источник | Что даёт |
|-------|------|----------|----------|
| Mistral | tavily_broad | Tavily | Широкий обзор |
| Mistral2 | duckduckgo | DuckDuckGo | Второй поисковик |
| GitHub | server_search | /opt/zinaida/ | Свои файлы и базы |
| Ollama | tavily_narrow | Tavily (цифры) | Конкретные данные |

**Подробнее:** `references/2026-07-11-agent-roles-and-search-sources.md`

### Ключевые изменения 11.07.2026
- Mistral2 переключен с Tavily на DuckDuckGo (бесплатно, без ключа, ddgs через pip install)
- GitHub переключен с Tavily на поиск по серверу (grep по /opt/zinaida/ + SQLite по базам)
- Ollama переключена с "без интернета" на узкий поиск по цифрам/датам
- DeepSeek V3 — только Раунд 4 и 2. Нигде больше. Удалён как агент сбора.
- Добавлен fallback: если GitHub упал — перекидываем на Mistral
- Парсер вопросов починен: теперь корректно парсит **Q1: ✅ ГОДНЫЙ** формат

### Файлы
- Ядро: `/opt/zinaida/scripts/deep_research.py`
- Оркестратор: `/opt/zinaida/scripts/deep_research_orchestrator.py`
- Отчёты: `/opt/zinaida/sandbox/deep_research/`

### HTML визуализация
- splash (карточки агентов): https://zinadchdp.duckdns.org/research/deep_research_splash.html
- report.html создаётся в папке каждого исследования

## Обзор
...
