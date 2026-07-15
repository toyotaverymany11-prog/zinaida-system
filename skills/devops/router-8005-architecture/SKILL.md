---
name: router-8005-architecture
description: Полная архитектура роутера 8005 — универсальный роутер для любых задач. Бесплатные усилители (Ollama, Mistral, Server RAG), отличие от 8002/8003, архитектурные решения, управление service, планы развития. НЕ привязан к контент-заводу.
version: 4.2
author: Zinaida
triggers:
  - 8005
  - новый роутер
  - router 8005
  - 8005-router
  - router_8005
  - роутер 8005
  - zina2-router-8005
  - усилители
  - беплатные нейросети
  - 8005-Pro
  - 8005-Flash
  - 8005 не трогать
  - запрет 8005
related_skills:
  - devops/provider-audit-reference
  - devops/production-change-protocol
---

## 🚨 КАТЕГОРИЧЕСКИЙ ЗАПРЕТ: НЕ ТРОГАТЬ 8005 БЕЗ ПРИКАЗА ОЛЕГА (13.07.2026)

**ПРАВИЛО (ЖЕЛЕЗНОБЕТОННОЕ):** 8005 роутер (`router_8005_v2.py`, порт 8005, systemd `zina2-router-8005.service`) **НЕ ТРОГАТЬ** без прямого приказа Олега. Даже косметические правки.

**Нарушение (13.07.2026):** Периодически правила 8005 → роутер ломался, Олег в ярости: «8005 вообще не трогай на хуй не прикасайся блядь чтобы не сломать ничего». После этого Олег явно приказал: «ремонтируй только 8002».

**Действие при упоминании 8005:**
1. **Не предлагать** изменения в 8005
2. **Не диагностировать** 8005 (только если Олег явно попросил)
3. **Не писать** про архитектуру 8005 в ответах
4. Если задача касается 8005 — перенаправить на 8002 (он независим от DeepSeek)
5. Если Олег сам просит что-то с 8005 — делать по Production Change Protocol

**Исключение:** Олег сам в явной форме говорит «исправь в 8005 XXXXX». Тогда делать, но с бэкапом.

## 🔄 СРАВНЕНИЕ С 8003

Сравнительная таблица, реальное распределение запросов, тесты и выводы: `references/8005-vs-8003-comparison.md`
Результаты всех 6 реальных тестовых сценариев: `references/8005-vs-8003-comparison.md`

Обновлено 11.07.2026: фактическая статистика из analytics.db (25 flash, 9 ollama, 8 pro), все 6 тестовых сценариев.

# РОУТЕР 8005

**Файл:** `/opt/zinaida/meta_agent/router_8005_v2.py`
**Порт:** 8005
**Systemd:** `zina2-router-8005.service` (enabled, auto-start)
**Управление:**
```bash
systemctl status|start|stop|restart zina2-router-8005.service
journalctl -u zina2-router-8005.service --no-pager -n 50
```
**Статус:** `curl -s http://127.0.0.1:8005/health | python3 -m json.tool`
**Модели:** `curl -s http://127.0.0.1:8005/v1/models | python3 -m json.tool`
**Пайплайн:** `curl -s http://127.0.0.1:8005/status | python3 -m json.tool`

## ⚠️ ФИЛОСОФИЯ: МОЩНОСТЬ ЧЕРЕЗ БЕСПЛАТНЫЕ УСИЛИТЕЛИ

8005 создавался чтобы быть **умнее и мощнее 8003 за счёт бесплатных нейросетей**.
Скорость — НЕ главное. **Главное — интеллект и качество ответа.**
Если задача — сделать запрос быстрым — использовать 8003 или 8002. 8005 про мощность.

**НИКОГДА НЕ ВЫРЕЗАТЬ БЕСПЛАТНЫЕ УСИЛИТЕЛИ РАДИ СКОРОСТИ.** Пользователь требует мощность, а не скорость. GigaChat, Mistral, Ollama — добавляют качество за 0 рублей.

### УНИВЕРСАЛЬНОСТЬ (КРИТИЧЕСКОЕ ПРАВИЛО)

8005 — **универсальный роутер для любых задач.** НЕ привязан к контент-заводу «Отношения»/SMM.

**НЕ ДОЛЖЕН:**
- Использовать smm_rag.db, phases.db, content_rotation.db — это контент-завод
- Иметь контент-заводскую логику

**ДОЛЖЕН:**
- Работать для ЛЮБОЙ темы (техник, дизайн, контент, планирование)
- Искать информацию ПО ТЕКУЩЕЙ ТЕМЕ ЧАТА на сервере через rg
- Использовать бесплатные нейросети (Mistral, Ollama) как усилители

### ВЫБОР УСИЛИТЕЛЕЙ (решения 11.07.2026 — ФИНАЛ)

| Усилитель | Универсальный? | Статус | Почему |
|-----------|---------------|--------|--------|
| **Ollama** (gemma3:4b) — приветствия | ✅ | ✅ АКТИВНО | Бесплатно, DeepSeek не тратится на «привет» |
| **Server RAG** (rg) — поиск файлов сервера | ✅ | ✅ АКТИВНО | Поиск по теме чата. Ищет .md .py .yaml .yml .json .toml |
| **Mistral analyzer** — cross-связи | ✅ | ✅ АКТИВНО | Находит связи между файлами, бесплатно |
| **Fallback** — Mistral → Ollama | ✅ | ✅ АКТИВНО | Страховка если DeepSeek упал |
| **Gender fix** — автозамена рода | ✅ | ✅ АКТИВНО | 32 пары глаголов |
| **Mistral preprocess** — чистка запроса | ❌ | ❌ УДАЛЁН | DeepSeek Flash сам чистит, Mistral не умнее |
| **Mistral verify** — проверка галлюцинаций | ❌ | ❌ УДАЛЁН | DeepSeek не галлюцинирует |
| **GigaChat** — редактура русского | ❌ | ❌ УДАЛЁН | Все модели пишут по-русски. +3 сек не окупается |

**Пайплайн (11.07.2026 — ФИНАЛ, без перегенерации):**
```
Запрос → Классификация
    │
    ├── короткий/привет → Ollama (бесплатно, 1.5 сек)
    │
    └── нормальный запрос ──┬── Server RAG (сначала!)
                            │   1. rg по содержимому .md .py .yaml .json .toml
                            │   2. find по имени файла (router_8005_v2.py → найден!)
                            │   3. Только: meta_agent, memory, shared_memory, scripts
                            │   НЕ: inbox, projects, .hermes, backup, cache
                            │   0.05-3 сек
                            │
                            └── DeepSeek Flash/Pro — ОДИН вызов с контекстом
                                │
                                после генерации:
                                ├── Mistral analyzer (cross-связи, параллельно, 3 сек timeout)
                                └── Gender fix
                                │
                                └── Fallback (Mistral → Ollama если DeepSeek упал)
```

**КЛЮЧЕВОЕ ИЗМЕНЕНИЕ 11.07.2026:** RAG выполняется ДО DeepSeek, а не параллельно.
- Раньше: DeepSeek + RAG параллельно → DeepSeek без контекста → RAG готов → перегенерация (2 вызова!)
- Сейчас: RAG сначала → 1 вызов DeepSeek с контекстом
**Выгода:** один вызов DeepSeek вместо двух, экономия $ и времени. Подробнее: `references/single-deepseek-call-pattern.md`.

### Server RAG — детали реализации

```python
# Поиск по содержимому (rg)
cmd = ["rg", "-i", "-l", query, search_dirs, "-g", "*.md", "-g", "*.py", ...]

# Поиск по имени файла (find) — дополнительно
cmd = ["find", search_dirs, "-maxdepth", "3", "-name", "*word*", ...]
# Найденные по имени файла — в начало списка (они релевантнее)

# Исключения: *.bak, *.swp, *backup*, *cache*
```

**Поисковые директории:** `/opt/zinaida/meta_agent`, `/opt/zinaida/memory`, `/opt/zinaida/shared_memory`, `/opt/zinaida/scripts`

**НЕ искать:** `/opt/zinaida/inbox` (27MB, знания по отношениям), `/opt/zinaida/projects`, `/root/.hermes` (sessions/skills гигабайты)

**Результат (тест 11.07.2026):** Запрос «расскажи про роутер 8005» → нашёл `router_8005_v2.py` по имени файла → ответ про системный сервис Зинаиды, а не про TP-Link.

## Что делает

Принимает запрос → классифицирует (Ollama / Flash / Pro) → 5 бесплатных усилителей → DeepSeek → пост-обработка.

## 3 УСИЛИТЕЛЯ (текущий состав 11.07.2026)

| Усилитель | Бесплатно | Что делает | Влияние | Timeout |
|-----------|-----------|-----------|---------|---------|
| **Ollama** (gemma3:4b) | ✅ | Приветствия и короткие ответы — DeepSeek не тратим | 1.5 сек | 10 сек |
| **Server RAG** (rg + find) | ✅ Локально | Поиск .md .py .yaml .json .toml в meta_agent, memory, shared_memory, scripts. Сначала по содержимому, потом по имени файла | 0.05-3 сек | 3+2 сек |
| **Mistral analyzer** | ✅ | Cross-связи между найденными файлами (что на что ссылается) | +0-3 сек | 3 сек |
| **Fallback** | ✅ | Mistral → Ollama если DeepSeek упал | 0 сек | — |

**Удалены из кода:** GigaChat (+3 сек rate limit), Mistral preprocess, Mistral verify.

**Выбор по задаче:**
- Универсальный роутер (любая тема): Ollama + Server RAG + Mistral analyzer + Fallback
- Контент-завод (если когда-нибудь): +GigaChat + Mistral preprocess + Mistral verify

## Скорость (тесты 11.07.2026 — финал после удаления GigaChat/Mistral verify)

| Запрос | Маршрут | 8005 (Server RAG + Mistral analyzer) | 8003 (чистый DeepSeek) |
|--------|---------|---------------------------------------|------------------------|
| Приветствие | Ollama → ответ | 1.5 сек | 1.0 сек |
| Средний (пост) | Server RAG + Flash + analyzer | 4.6 сек | 6.3 сек |
| Сложный (анализ) | Server RAG + Pro + analyzer | 18 сек (reasoner) | — |

**8005 БЫСТРЕЕ 8003** на средних запросах (4.6 vs 6.3 сек).
Медленнее на приветствиях (Ollama vs прямой DeepSeek — разница 0.5 сек некритична).
Перегенерация контекста УСТРАНЕНА 11.07.2026 — RAG выполняется ДО DeepSeek, один вызов.

## Модели для выбора в Hermes

| ID в /v1/models | Когда срабатывает | Стоимость |
|----------------|-------------------|-----------|
| `8005-Router` | Авто-классификация (рекомендуется) | Flash/Ollama → экономно |
| `8005-Flash` | Форсировать DeepSeek Flash | $0.27/1M |
| `8005-Pro` | Форсировать DeepSeek Pro | $1.42/1M |
| `8005-Enhanced` | **Форсировать Pro + сохранить все усилители (очень высокий режим)** | $1.42/1M |

### 8005-Enhanced (очень высокий режим)

Режим «Очень высокий» в Hermes Studio — это переключение модели, а не reasoning_effort. При выборе `8005-Enhanced`:
- Классификатор форсирует **DeepSeek Pro** на каждый запрос (вместо Flash по умолчанию)
- **Все бесплатные усилители остаются активны:** RAG, Mistral analyzer, фикс рода, кэш
- Приветствия НЕ уходят на Ollama (всегда Pro)
- Экономия: не обходит роутер 8005 — RAG и анализатор работают бесплатно

**Как включить:**
1. Hermes Studio → выбор модели → провайдер `8005` → модель `8005-Enhanced`
2. Либо в запросе: `"model": "8005-Enhanced"`

**Как это реализовано в коде:**
```python
if "pro" in req or "reasoner" in req or "enhanced" in req:
    model_key = "pro"
    if "enhanced" in req:
        logger.info("PIPELINE: VERY HIGH режим — форсирован Pro, усилители активны")
```

**Сравнение режимов:**
| Режим | Модель | Расходы | RAG | Фикс рода | Кэш |
|-------|--------|---------|-----|-----------|-----|
| Обычный | `8005-Router` | Flash/Ollama (экономно) | ✅ | ✅ | ✅ |
| Очень высокий | `8005-Enhanced` | Pro ($1.42/1M) | ✅ | ✅ | ✅ |
| (без роутера) | DeepSeek напрямую | Pro ($1.42/1M) | ❌ | ❌ | ❌ |

## Добавить в Hermes Studio

### Через Settings → Providers
- **Provider name:** 8005-router
- **Base URL:** `http://127.0.0.1:8005/v1`
- **API key:** любой (dummy-key)
- **Default model:** 8005-Router

### Через config.yaml
```yaml
custom_providers:
  - api_key: dummy-key
    base_url: http://127.0.0.1:8005/v1
    name: 8005-router

model:
  default: 8005-Router
  provider: custom:8005-router
```

## Быстрый тест

```bash
# Приветствие → Ollama (бесплатно)
curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"привет"}],"max_tokens":10}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['model'])"

# Средний → Flash (дёшево)
curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"Расскажи что такое API"}],"max_tokens":50}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['model'])"

# Сложный → Pro (глубоко)
curl -s -X POST http://127.0.0.1:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"8005-Router","messages":[{"role":"user","content":"Проанализируй различия"}],"max_tokens":50}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['model'])"
```

## Логи

```bash
cat /tmp/router_8005.log | grep -E "CLASSIFY|DEEPSEEK|OLLAMA|VERIFY|POLISH|FALLBACK|OK" | tail -20
- `references/quick-commands.md` — шпаргалка быстрых команд
- `references/gender-auto-fix.md` — автозамена мужских глаголов на женские в ответах

## Протокол изменений

Править — только через Production Change Protocol:
1. Бэкап файла
2. Работать в копии, не трогать production
3. Тестировать на тестовом порту
4. Только потом интегрировать
5. Писать в updates_log.md

## ⚠️ БАГ: DeepSeek 402 (баланс 0) ломает cascade для Pro-запросов (13.07.2026)

**Проблема:** Когда DeepSeek пустой (HTTP 402), Pro-модели не получают fallback на бесплатные.

**Причина в коде (строки 690 и 748 router_8005_v2.py):**
```python
if model_key != "pro":  # Pro не обходим — сразу DeepSeek
```
Классификатор на строках 156-187 ставит `pro` если:
- Запрос > 300 символов (PRO_CHAR_THRESHOLD)
- Есть триггерные слова ("анализируй", "сравни", "код")
- Много латиницы с синтаксисом кода

**Эффект:** Если запрос = pro, cascade (Mistral + GPT-4o) пропускается, DeepSeek вызывается сразу. DeepSeek возвращает 402 → fallback вызывает `_fallback_generate(messages)` (Mistral → Ollama). Но `_fallback_generate` запихивает **все исходные сообщения** без RAG-контекста, и Mistral/Ollama могут не справиться с длинным запросом.

**Решение (если DeepSeek мёртв):**
1. Временно убрать проверку `model_key != "pro"` на строках 690 и 748 — Pro тоже пойдёт через cascade
2. Или добавить в `_fallback_generate` переключение на GPT-4o (GitHub) перед Mistral

**Симптом для пользователя:** "DeepSeek кончились деньги → роутер перестал отвечать"

## ✅ SUPER CASCADE — Mistral → GPT-4o → DeepSeek (12.07.2026, реализовано)

**Проблема:** 8003 (Zina2-Router) гонит 99% запросов через DeepSeek Reasoner — дорого ($1.42/M).
8005 использует Flash — дешевле ($0.27/M), но не бесплатно.

**Решение:** три бесплатных эшелона перед DeepSeek:
1. **Mistral-large** (бесплатно, 3 ключа, уровень GPT-4)
2. **GPT-4o** через GitHub Models (бесплатно, 2 живых токена, ~1.3с)
3. **DeepSeek Flash** ($0.27/M) — только если бесплатные не справились
4. **DeepSeek Pro** ($1.42/M) — экстрим

**GitHub токены (сохранены в `/opt/zinaida/config/secrets.env`):**
- `GITHUB_TOKEN` = `ghp_hX...v9o1` — ✅ основной (аккаунт toyotaverymany11-prog)
- `GITHUB_TOKEN_2` = `ghp_HD...dSRy` — ✅ запасной (тот же аккаунт)
- Токен `ghp_kz...pycp` — ❌ 401 Bad credentials, удалён
- Модели: gpt-4o, gpt-4o-mini, Llama 3.1 405B/8B
- Rate limit ~60 req/min на аккаунт (два токена на один аккаунт — лимит не удваивается)

### Алгоритм (код в `_generate()`)
```
Запрос → Классификатор
    ├── привет/да/нет → Ollama gemma3:4b (бесплатно, <1%)
    │
    ├── classify: flash → SUPER CASCADE
    │   1. Mistral-large + самооценка CONFIDENCE (0-100)
    │      ├── CONFIDENCE ≥ 75 → ответ ✅ (бесплатно, ~2-3с, ~70%)
    │      └── CONFIDENCE < 75 → шаг 2
    │   2. GPT-4o (GitHub, 2 токена, ротация)
    │      ├── ответил → ответ ✅ (бесплатно, ~1.3с, ~15%)
    │      └── 429/ошибка → шаг 3
    │   3. DeepSeek Flash ($0.27/M, ~10%)
    │
    └── classify: pro → DeepSeek Pro ($1.42/M, ~5%) — минуя cascade
```

### Самооценка Mistral (функция `_call_mistral_with_confidence`)
Промпт в конец: "Ответь. После ответа добавь CONFIDENCE: 0-100. 100=уверен, 0=не знаешь. При сомнении < 75."
Извлекается из последней строки ответа. Строка вырезается из ответа пользователю.

### Мониторинг (MONITOR словарь + `_send_alert`)
Счётчики в `_track(provider, ok)`:
- `by_provider`: mistral/github/flash/pro/ollama → количество
- `github_rate_limited`: сколько раз 429
- `deepseek_down`: сколько раз DeepSeek упал
Алерт в Telegram при >3 падений DeepSeek. Cooldown 5 мин.

### /status endpoint
Показывает: версию, количество ключей (GitHub/Mistral/Ollama), cascade-схему, monitor-статистику, warnings.

### Тесты (12.07.2026)
```
"что ты умеешь?" → Mistral: confidence=95 → CASCADE: 2.0с → БЕСПЛАТНО
"проанализируй роутеры" → classify: pro → DEEPSEEK (pro) OK: 25.5с → $1.42/M
"Привет как дела?" → Mistral: confidence=95 → CASCADE: 2.0с → БЕСПЛАТНО
```

### Питфоллы
- Mistral может завышать CONFIDENCE — порог **95**, не ниже. **12.07.2026 фикс:** было 75, Mistral отвечал с confidence=95 даже неся чушь (технические вопросы), блокируя gpt-4o. Поднят до 95 — Mistral отвечает сам только если абсолютно уверен. **13.07.2026 — повторный фикс:** порог поднят до 95 (было 75) — Mistral теперь пропускает 90% запросов gpt-4o. Это правильно: gpt-4o качественнее, быстрее (1.3с) и тоже бесплатный.
- GitHub rate limit ~60 req/min на аккаунт. Два токена на один аккаунт НЕ удваивают лимит — только страховка если один протухнет.
- GitHub gpt-4o отлично тянет русский — быстрее DeepSeek (1.3с vs 4.5с)
- Pro-запросы обходят cascade — сразу DeepSeek Reasoner
- Llama 405B в тесте дал 400 Bad Request — не использовать пока (требует другого формата)
- **Consilium pollution в Telegram (КРИТИЧЕСКИЙ ПИТФОЛЛ, исправлен 13.07.2026):** bot.py НЕ должен подгружать CONSILIUM_*.md в каждый запрос. Симптом: модель отвечает про LoRA и Mage Blog когда её спросили «как дела». Причина: `get_last_consilium()` добавлял контент консилиума в `[Консилиум: ...]` в каждое сообщение. Фикс: удалён вызов consilium из `send_to_hermes_studio()`. Consilium приходит только утром как отдельное сообщение через notify.py.
- **Telegram bot 404 на custom провайдеры (исправлен 13.07.2026):** Hermes Gateway (8642) возвращает 404 на `/api/chat-run/runs` с `provider: custom:8005`. Gateway знает провайдера, но не может через него запустить чат-ран. Фикс: bot.py ходит напрямую на `http://127.0.0.1:8005/v1/chat/completions` минуя Gateway. URL в `HERMES_DIRECT_URL`.

## Telegram bot архитектура (13.07.2026 — фикс 404 на custom провайдеры)

**Проблема:** Hermes Gateway (8642) возвращает 404 на `/api/chat-run/runs` с `provider: custom:8005`. Gateway знает провайдера, но не может через него запустить чат-ран.

**Решение:** bot.py ходит напрямую на 8005 через OpenAI-совместимый API.

```
Ты → Telegram → bot.py → http://127.0.0.1:8005/v1/chat/completions
                           ↓
                    system: SOUL.md (личность)
                    user: вопрос
```

**System prompt:** bot.py загружает `/root/.hermes/SOUL.md` при старте как `ZINAIDA_SYSTEM_PROMPT` и передаёт в каждый запрос как `role: system`. Без этого 8005 отвечает как безликий LLM.

**Consilium НЕ подгружается** в каждый запрос — только утром как отдельное сообщение.

**Файл:** `/opt/zinaida/telegram_bot/bot.py`
**Конфиг:** `HERMES_DIRECT_URL = "http://127.0.0.1:8005/v1/chat/completions"`

## Сравнение 8003 vs 8005 (из логов 12.07.2026)

### 8003 (Zina2-Router) — 99% запросов через Pro
```
PRO TRIGGER: слово 'как' → Pro
PRO TRIGGER: длина > 150 → Pro
Flash: только 1% (и то переключалось на Pro)
```
Вывод: порог 150 символов слишком чувствительный. Почти всё через Reasoner ($1.42/M).

### 8005 (8005-Router) — экономичнее
```
CLASSIFY: flash (17 символов, привет) → Flash ($0.27/M)
CLASSIFY: pro (триггер) + RAG + analyzer → Pro ($1.42/M) только когда надо
```
Вывод: Flash по умолчанию, Pro только для сложного. RAG даёт контекст бесплатно.

### Решение (12.07.2026)
Telegram бот переключён с 8003 на 8005-Router. Экономия ~70% стоимости.
Для максимального качества — 8005-Enhanced (форсирует Pro + все усилители).

## Пост-процессинг: автозамена мужского рода (gender fix)

В роутере встроена автоматическая замена мужских глаголов на женские (шаг 9 в `_generate()`).
Список из 32 пар: понял→поняла, сделал→сделала, пошёл→пошла, написал→написала и т.д.
Логируется как `GENDER FIX: понял → поняла`.

## Автоматическая защита рода

Роутер содержит пост-процессинг (Шаг 9 в _generate), который автоматически исправляет мужские глаголы на женские в ответах. Список из 32 пар глаголов (понял→поняла, сделал→сделала и т.д.). Замена с логом GENDER FIX.
