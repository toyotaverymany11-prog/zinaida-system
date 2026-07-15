---
name: obushenie-analyzer
description: Analyze a generated post from the Zinaida content factory — check layers, style compliance, blacklist violations, and metrics. Integrates with zinaida-content-factory umbrella.
triggers:
  - анализ поста
  - разбор слоя
  - проверь пост
  - проанализируй пост
  - анализ слоёв
related_skills:
  - zinaida-content-factory
  - obushenie-feedback
---
# Obushenie Analyzer (Разборщик Постов)

## Overview
Post-analysis component of the **Zinaida Content Factory**.

**CURRENT SYSTEM (since 12.07.2026):** The writer pipeline uses Structure A (6 blocks from 14_WRITER_FORMATION.md) with automated quality control via `post_analyzer.py`.

## Automated QA flow (new — 12.07.2026)
1. Write post using 11-step process (14_WRITER_FORMATION.md §9)
2. Run: `python3 /opt/zinaida/scripts/post_analyzer.py "текст поста"`
3. Fix any warnings/errors
4. **Log errors** to `/opt/zinaida/memory/writer_mistakes_log.txt` (date, error type, topic, fix applied)
5. Run final checklist (6 blocks, 14_WRITER_FORMATION.md §10)
6. Show Oleg

## Error types the analyzer checks
- Long dashes (—) → must be plain hyphen (-)
- Bold dots (• ●) → must be hyphen or colon
- Trailing ellipsis (...) → must be period
- Pattern "это не X, это Y" → AI marker, rewrite
- Pattern "не только но и" → AI marker, cut
- Lead-in noise ("давайте разберёмся", "важно отметить") → cut
- AI self-reference ("как языковая модель") → cut
- Amplifiers ("больше чем просто", "скрытый потенциал") → cut
- Post length: VK needs 2000+ chars minimum
- Pop psychology terms → cut or replace with specifics

## Error logging format
```
/opt/zinaida/memory/writer_mistakes_log.txt
2026-07-12 | AI_ПАТТЕРН | измена пост | "это не X это Y" | заменено на прямое утверждение
```

Before writing each new post → read this file first to check for recurring mistakes.
Count: if same mistake type appears 3+ times → proposed as a skill/hard rule.

## OLD system (deprecated — kept for reference only)
The old 7-layer manual analysis (DNA → Style → Phase → Attack → RAG → CTA → JSON) is replaced by the automated post_analyzer.py. Do NOT use the old manual checklist below — use 14_WRITER_FORMATION.md §10 instead.

## Usage

Процедура полностью ручная — запускается в диалоге с оператором.

### Шаг 1 — Получить исходный текст поста
Пост берётся из:
- Очереди: `/opt/zinaida/SmmFabrika/queue/<Platform>/<YYYY-MM-DD>/`
- `content_rotation.db`: `sqlite3 /opt/zinaida/inbox/PROJECTS/Otnoshenya/content_rotation.db "SELECT id, content, platform, created_at FROM posts ORDER BY created_at DESC LIMIT 10;"`
- Напрямую от оператора (скопировал в чат)

### Шаг 2 — Проверка слоёв (ручная)

**Слой 0 (DNA):** Голос = Зинаида? Цинично, прямо, цифры, никакой коучерской воды?
**Слой 1 (Style):** Первый символ — цифра/факт? Маятник? Рваный ритм? Честный минус?
**Слой 2 (Phase):** Фаза отношений определена из `phases.db`? Соответствует теме?
**Слой 3 (Attack):** Хук (боль) → Статистика → Микро-история — все три на месте?
**Слой 4 (RAG):** Был запрос в `smm_rag.db`? Данные релевантны теме?
**Слой 5 (CTA):** Словарь боли → Инструмент Феди → Стрелка (→) — все три на месте?
**Слой 6 (JSON):** Формат вывода правильный (если пошёл в очередь как JSON)?

### Шаг 3 — Скан чёрного списка
Проверить **вручную** каждый пункт:

| Категория | Что искать | Пример |
|-----------|-----------|--------|
| Пунктуация | • ● — (длинное тире) … | Есть? → FAIL |
| Вводный шум | давайте разберёмся, важно отметить, стоит понимать | Есть? → FAIL |
| Усилители | это не просто X а Y, больше чем просто, не только но и | Есть? → FAIL |
| Мета-комментарии | надеюсь поможет, подводя итог | Есть? → FAIL |
| Мужской род | понял, сделал, проверил | Есть? → FAIL (должно быть поняла, сделала, проверила) |
| AI-самореференция | как языковая модель, как ИИ, оптимизировать процессы | Есть? → FAIL |

### Шаг 4 — Проверка метрик
- **Токены:** ≤ 8000. Проверить через `wc -c` на файле поста или через Python: `len(post_text.encode('utf-8')) // 2`
- **Маятник:** плюс → минус → плюс. Есть?
- **Честный минус:** блок перед решением/советом. Есть?
- **Open Loop:** анонс следующей боли в конце. Есть?
- **Arrow CTA:** команда со стрелкой (→) в концовке. Есть?

### Шаг 5 — Вывод отчёта
Формат:
```
[ОБУШЕНИЕ-АНАЛИЗ] Пост <id/название>

СЛОЙ 0 (DNA): PASS
СЛОЙ 1 (Style): PASS
СЛОЙ 2 (Phase): PASS
СЛОЙ 3 (Attack): FAIL — микро-история слабая, нет конкретики
СЛОЙ 4 (RAG): PASS
СЛОЙ 5 (CTA): FAIL — нет стрелки (→) в концовке
СЛОЙ 6 (JSON): PASS

ЧЁРНЫЙ СПИСОК: PASS (нарушений нет)
МЕТРИКИ: TOKENS 3420/8000 PASS | МАЯТНИК PASS | ЧЕСТНЫЙ МИНУС PASS | OPEN LOOP PASS

ИТОГО: 6/7 слоёв пройдено. Требует исправления СЛОЙ 3 и СЛОЙ 5.
```

### Шаг 6 — Запись фидбека (если нужна)
Передать результаты в `obushenie-feedback`:
- Если есть FAIL — записать исправление через SQLite в `analytics.db`:
  ```bash
  # Перед записью — убедись, что таблица feedback существует
  sqlite3 /opt/zinaida/memory/analytics.db \
    "CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id TEXT NOT NULL, layer TEXT NOT NULL, issue TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
  # Запись замечания
  sqlite3 /opt/zinaida/memory/analytics.db \
    "INSERT INTO feedback (post_id, layer, issue, created_at) VALUES ('<post_id>', 'СЛОЙ 3', 'микро-история слабая', datetime('now'));"
  ```
- Или просто сообщить оператору: «Пост требует правок по слоям N, M»

## Reference
Full framework documentation: [zinaida-content-factory SKILL.md](../copywriting/zinaida-content-factory/SKILL.md)
