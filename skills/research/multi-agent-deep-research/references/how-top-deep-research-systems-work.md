# Как устроены топовые Deep Research системы

## Источники (10.07.2026)
- ByteByteGo: How OpenAI, Gemini, and Claude Use Agents to Power Deep Research
- Anthropic Engineering Blog: How we built our multi-agent research system (Jun 13, 2025)
- Google AI: Gemini Deep Research Agent API docs
- Abacus AI Deep Agent documentation + KDnuggets review
- PromptLayer: How OpenAI's Deep Research Works
- TECHSY: 13 Best AI Search APIs for AI Agents (2026)
- OpenAI: Introducing deep research

---

## Общий паттерн архитектуры

Все топ-системы (OpenAI, Anthropic, Google, Abacus) пришли к одной и той же базовой структуре:

```
Пользователь → Оркестратор (сильная модель) → планирует
  → 3-5 параллельных агентов (лёгкие модели) → ищут, читают, анализируют
  → Синтезатор (сильная модель) → собирает отчёт с цитатами
```

## Ключевые цифры (Anthropic)

| Метрика | Значение |
|---------|----------|
| Multi-agent vs single-agent | **+90% effective** (по внутренним тестам) |
| Variance from token usage | **80%** — чем больше токенов, тем лучше результат |
| Time reduction (3-5 parallel agents) | **до 90%** |
| Token consumption vs standard chat | **~15× больше** |

## OpenAI Deep Research

**Основа:** o3 reasoning model, RL-обучение на simulated research environments.
**Фазы:**
1. Clarifying the task (уточняющие вопросы)
2. Decompose & Plan (декомпозиция)
3. Iterative Web Searching (многократные поиски)
4. Read & Analyze (парсинг HTML, PDF, images, code)
5. Synthesize into structured reports

**Stopping mechanism:**
- Coverage-based: 2+ независимых источника на под-вопрос
- Budget-driven: 30 min, 60 searches, 150 pages, 200 reasoning loops

## Gemini Deep Research

**Основа:** Gemini 3 Pro через Interactions API (background execution).
**Ключевое отличие:** Collaborative planning — сначала показывает план, пользователь утверждает.
**Интеграция:** Gmail, Drive, Chat (персонализированные отчёты).
**Бенчмарки:** 46.4% HLE, 66.1% DeepSearchQA, 59.2% BrowseComp.

## Аналитика по поисковым API (2026)

### Рынок после смерти Bing Search API (Aug 2025)
Bing API заменён на "Grounding with Bing Search" внутри Azure — цена выросла на 40-483%.

### Рейтинг (по TECHSY, Jun 2026)

| API | Бесплатный лимит | Latency | Особенность |
|-----|-----------------|---------|-------------|
| **Tavily** | 1000/мес | 2.1s | Лучший для RAG, готовый контент + цитаты |
| **Brave Search** | **2000/мес** | **0.8s** | Независимый индекс, MCP сервер, LLM Context endpoint |
| **Exa** | $10 trial | 1.2s | Нейронный поиск (понимает смысл, не ключевые слова) |
| **SerpAPI** | 100 trial, $50/5k | 1.2s | 30+ движков, SERP wrapper (нужен extract) |
| **CatchAll** | 2000 credits | ~сек | Кластеризация Leiden, LLM validation |

## Abacus AI Deep Agent

**Вывод:** 20+ моделей, 4 уровня effort (xLow → Max).
**Ключевая фича:** полноценный Linux environment — может писать код, ставить пакеты, строить дашборды.
**Время:** 5-25 минут на типичную задачу.
**Оценка:** 9/10 от KDnuggets — «компетентный автономный ассистент».

### Структура уровней effort
- **Auto** (default) — автоматический выбор
- **High / xHigh** — дорогие модели (GPT 5.5, Opus 4.8)
- **Max (Fable 5)** — Claude Fable 5 (самый сильный кодинг)
- **xLow** — быстрые open-source (GLM 5.2, Kimi 2.7)

## Что это значит для нашей реализации

1. Наша 4-раундная архитектура **совпадает** с тем, как делают лидеры. Мы не изобретаем велосипед.
2. Наш killer feature — **раунд вопросов** (агенты формулируют осмысленные запросы). OpenAI так не делает — они просто перебирают страницы. Anthropic запускает параллельных агентов без осмысления.
3. Нам не хватает **интерактивного планирования** (показывать план Олегу перед запуском).
4. Стоп-механизм — **2+ источника** на каждое утверждение. DeepSeek это делает в Round 4.
5. Поисковые API: Tavily хватает для старта. При росте объёмов — добавить Brave Search (2000 запросов бесплатно).
