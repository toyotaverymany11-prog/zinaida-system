# Session 12.07.2026 — Infidelity VK post & systemic fixes

## Key failures & fixes

### Failure 1: Mixed vectors
Post started as научпоп then switched to detective. Oleg: "какая-то хуйня, не связано с началом".
**Fix:** One vector from first line to last. Choose A (scientific), B (detective), or C (personal guide). Never mix.

### Failure 2: "это не то, что ты думаешь" in headline
Oleg: "на хуя ты это сюда вставила". This is the "это не X, это Y" pattern.
**Fix:** Added to post_analyzer.py + 02_blacklist.md.

### Failure 3: "Я не говорю тебе Х. Я говорю Y" pattern
Same AI-pattern flavor. Added to post_analyzer.py + 02_blacklist.md.

### Failure 4: Two statistics in a row (74% + 42%)
**Fix:** ONE statistic per post. Spread if two needed.

### Failure 5: CTA "я собрала коллекцию паттернов" — boring
**Fix:** CTA rules:
- ❌ "я собрала/нашла/выделила/подготовила"
- ✅ "я разработала/у меня есть инструмент/моя авторская разработка"
- Name instrument with capital letter

### Failure 6: No red thread
**Fix:** Красная нить (Шаг 1.5): "Читательница получит: [конкретный результат]". Every block checked against it.

## Changes made
1. **14_WRITER_FORMATION.md**: Красная нить, CTA rules, one-stat rule
2. **02_blacklist.md**: new AI patterns added
3. **post_analyzer.py**: 17 checks (2 new)
4. **writer_mistakes_log.txt** created
