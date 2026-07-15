---
name: obushenie-feedback
description: Record post-analysis feedback into the Zinaida learning loop — corrections, layer-level issues, and quality flags. Feeds into the EMA-based curator weights. Integrates with zinaida-content-factory umbrella.
triggers:
  - записать фидбек
  - сохранить правки
  - зафиксировать ошибку
  - feedback
  - исправление
related_skills:
  - zinaida-content-factory
  - obushenie-analyzer
---
# Obushenie Feedback (Запись Фидбека)

## Overview
Feedback recording tool for the **[Zinaida Content Factory](../copywriting/zinaida-content-factory/)**. Records layer-level corrections after obushenie-analyzer output, which feeds into the EMA-based curator math (Monday weight adjustments).

## Usage

Процедура полностью ручная — выполняется в диалоге с оператором.

### Вариант A — Прямая запись в SQLite

**Перед первой записью — проверь, что таблица `feedback` существует:**

```bash
# Проверка и создание таблицы, если её нет
sqlite3 /opt/zinaida/memory/analytics.db << 'EOF'
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT NOT NULL,
  layer TEXT NOT NULL,
  issue TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
EOF
```

**Затем запись:**

```bash
sqlite3 /opt/zinaida/memory/analytics.db \
  "INSERT INTO feedback (post_id, layer, issue, created_at) VALUES ('<post_id>', 'LAYER_PREFIX', 'описание проблемы', datetime('now'));"
```

Где `<post_id>` — ID поста из очереди или `content_rotation.db`.

### Вариант B — Устная (оператор не требует записи в БД)
Просто зафиксировать в диалоге: «Записала фидбек по слою N. Правка учтена для следующей генерации.»

### Вариант C — Накопительный список сессии
Если за сессию набралось несколько правок — собрать в один batch-запрос:

```bash
sqlite3 /opt/zinaida/memory/analytics.db << 'EOF'
INSERT INTO feedback (post_id, layer, issue, created_at) VALUES
  ('post_001', 'СЛОЙ 3', 'хук без цифры', datetime('now')),
  ('post_002', 'СЛОЙ 5', 'CTA без стрелки', datetime('now')),
  ('post_003', 'BLACKLIST', 'мужской глагол "понял"', datetime('now'));
EOF
```

## Layer Labeling Convention

Use these prefixes for the feedback string:

| Prefix | Layer | Example Problem |
|--------|-------|-----------------|
| `СЛОЙ 0:` | DNA | "голос не Зинаиды, слишком мягко" |
| `СЛОЙ 1:` | Style | "нет честный минус, нет маятника" |
| `СЛОЙ 2:` | Phase | "фаза не соответствует теме" |
| `СЛОЙ 3:` | Attack | "хук слабый, нет цифры в первой строке" |
| `СЛОЙ 4:` | RAG | "чанк не релевантен теме" |
| `СЛОЙ 5:` | CTA | "стрелка отсутствует, команда размыта" |
| `СЛОЙ 6:` | JSON | "формат невалидный" |
| `BLACKLIST:` | — | "мужской глагол 'понял' вместо 'поняла'" |
| `TOKENS:` | — | "превышен лимит 8000" |

## Examples
```bash
# Записать исправление стиля
sqlite3 /opt/zinaida/memory/analytics.db \
  "INSERT INTO feedback (post_id, layer, issue, created_at) VALUES ('post_001', 'СЛОЙ 1', 'нет рваного ритма, предложения слишком гладкие', datetime('now'));"

# Записать исправление слоя атаки
sqlite3 /opt/zinaida/memory/analytics.db \
  "INSERT INTO feedback (post_id, layer, issue, created_at) VALUES ('post_002', 'СЛОЙ 3', 'хук открывается с приветствия, не с цифры', datetime('now'));"

# Записать нарушение чёрного списка
sqlite3 /opt/zinaida/memory/analytics.db \
  "INSERT INTO feedback (post_id, layer, issue, created_at) VALUES ('post_003', 'BLACKLIST', 'использовано \"важно отметить\" во втором абзаце', datetime('now'));"
```

## Feedback Loop Integration
Recorded feedback accumulates in analytics.db. Every Monday, the curator runs EMA:
```
new_weight = old_weight * 0.8 + target_metric * 0.2
```
This adjusts the Attack Layer weights for the next generation cycle.

## Reference
Full framework documentation: [zinaida-content-factory SKILL.md](../copywriting/zinaida-content-factory/SKILL.md)
