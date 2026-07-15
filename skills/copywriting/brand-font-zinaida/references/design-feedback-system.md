# СИСТЕМА УЧЁТА ДИЗАЙН-ФИДБЕКА

Создана 10.07.2026 после того как Олег выявил повторяющуюся ошибку:
«Ты должна была записывать какие картинки я хвалю, ты должна была это фиксировать».

## Проблема

Я не вела реестр того, какие изображения Олег хвалил/ругал. В памяти висел
ложный «победитель» (cover_V2_try2.jpg), который на самом деле Олег назвал
«говно собачье». Результат: в каждом новом чате я начинала с нуля,
генерировала то, что уже отвергнуто, тратила деньги на Replicate.

## Решение

### 1. SQLite база: `/opt/zinaida/memory/design_assets.db`

Три таблицы:

**assets** — каждая сгенерированная картинка:
- id, file_path, file_name, model, prompt, prompt_hash
- aspect_ratio, platform, asset_type (cover/portrait/quote/scene/avatar)
- date_generated, size_bytes, tags, status

**feedback** — каждый фидбек Олега:
- id, asset_id (FK), verdict, rating, oleg_quote, what_to_fix
- date_feedback, chat_id

**generation_log** — аудит:
- id, asset_id, action, details, timestamp

Verdicts: praise / approved / reject / wip / not_shown

### 2. Скрипты

**`/opt/zinaida/scripts/fix_design_feedback.py`** — запись фидбека:
```bash
python3 fix_design_feedback.py <file_path> <verdict> "цитата Олега"
```

**`/opt/zinaida/scripts/register_design.py`** — регистрация генерации:
```bash
python3 register_design.py <file_path> --model <model> --prompt "<prompt>" --type <type> --tags "<tags>"
```

### 3. Железное правило (в AGENTS.md)

ЛЮБОЙ фидбек Олега по дизайну → НЕМЕДЛЕННО в базу.
Без задержек. Без «потом запишу». Без размышлений.
Даже если Олег просто сказал «норм» или «говно» — записать.

При старте любого чата по дизайну — читать базу:
```sql
SELECT * FROM feedback ORDER BY id DESC LIMIT 10
```

### 4. Что уже в базе (по состоянию на 10.07.2026)

26 assets, 10 feedback записей:
- 7 approved (портреты, аватары, цитаты)
- 1 praise (vk_cover_arch_ref.jpg — «охуенный вариант, золотые буквы»)
- 2 reject (cover_V2_try2.jpg — «говно собачье serif на skyline»;
           cover_final_gold.jpg — «хуета стрёмная»)
- 16 not_shown (тесты A/B/C, черновики)

### 5. Интеграция с design_feedback.md

Параллельно ведётся текстовый лог `/opt/zinaida/shared_memory/design_feedback.md`
для человекочитаемой истории. Каждый фидбек дублируется туда.
