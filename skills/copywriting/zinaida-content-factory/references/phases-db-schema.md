# phases.db — Actual Schema & Query Guide

## Table Structure

```sql
CREATE TABLE phases (
    phase_id        TEXT,        -- format: А_01, А_07, Б_02, В_18, Г_04, Д_05, Е_06
    pain_point      TEXT,        -- primary text description of the phase pain
    trigger_action  TEXT,        -- what the woman actually does
    micro_scenario  TEXT,        -- concrete scene description
    risk            TEXT,        -- what goes wrong
    opportunity     TEXT,        -- what can be gained
    hook_template_id TEXT,       -- references hooks/templates/<id>.md
    stat_mechanic_id TEXT,       -- references stats/mechanics/<id>.md
    PRIMARY KEY(phase_id, pain_point)
);
```

## ⚠️ CRITICAL DIFFERENCES FROM THE SKILL

| Skill says | Actual | Impact |
|-----------|--------|--------|
| Column `name` | Column `pain_point` | All `WHERE name LIKE` queries fail |
| Phase format `А4, Б2, В3` | Actual format `А_07, Б_02, В_18` | Direct phase_id queries fail |
| Content plan uses `А4, Г1` shorthand | DB has `А_07, Г_04` | Must map: А4→А_07, Г1→Г_04 |

## Complete Phase List (all 41)

### Group А (Начало, неопределённость)
- `А_01` — страх отказа при знакомстве
- `А_07` — активный поиск, страх отвержения, проверка телефона каждые 5 минут. **«Почему он молчит»**
- `А_08` — пассивное ожидание, высокий уровень самооценки, отказ от компромиссов
- `А_09` — (theme undiscovered)
- `А_10` — (theme undiscovered)
- `А_11` — (theme undiscovered)
- `А_12` — (theme undiscovered)

### Group Б (Статус, тревога)
- `Б_02` — тревога неопределённости статуса
- `Б_13` to `Б_17` — (theme undiscovered)

### Group В (Конфликты, остывание)
- `В_03` — остывание партнёра
- `В_18` to `В_24` — (theme undiscovered)

### Group Г (Избегание, отдаление)
- `Г_04` — страх измены после корпоратива, «молчит три дня после ссоры»
- `Г_25` to `Г_30` — (theme undiscovered)

### Group Д (Паттерны, кризис)
- `Д_05` — восстановление после кризиса
- `Д_31` to `Д_36` — (theme undiscovered)

### Group Е (Разрыв)
- `Е_06` — страх одиночества после расставания
- `Е_37` to `Е_41` — (theme undiscovered)

## Correct Query Patterns

```sql
-- Search by topic keyword
SELECT phase_id, pain_point, trigger_action, risk, opportunity
FROM phases
WHERE pain_point LIKE '%молч%'
   OR pain_point LIKE '%отверж%'
   OR pain_point LIKE '%страх%';

-- Get details for a specific phase
SELECT * FROM phases WHERE phase_id = 'А_07';

-- List all phases with their core pain
SELECT phase_id, substr(pain_point,1,60) AS pain_short
FROM phases ORDER BY phase_id;

-- Find the linked stat file for a phase
SELECT phase_id, stat_mechanic_id FROM phases WHERE phase_id = 'А_07';
-- Then read: stats/mechanics/stat_batch2_28.md

-- Find the linked hook template
SELECT phase_id, hook_template_id FROM phases WHERE phase_id = 'А_07';
-- Then read: hooks/templates/hook_batch2_12.md
```

## Content Plan Phase Mapping

The content_plan table (in content_rotation.db) uses SHORT format (A4, Г1).
Map to DB format by replacing the digit with underscore-zero:

| Content Plan | DB phase_id | Example topic |
|-------------|-------------|---------------|
| A4 | А_07 | Почему он молчит |
| Б2 | no exact match | (search pain_point) |
| Г1 | Г_04 | Гостинг / молчит после ссоры |
| В2 | В_03 or В_18 | Хлебные крошки |
| Д1 | Д_05 | Измена / признаки |

If no direct match exists — search `pain_point LIKE '%keyword%'` with the pain keyword.
