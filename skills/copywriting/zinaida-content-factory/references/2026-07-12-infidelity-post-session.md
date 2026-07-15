# Session: 12.07.2026 — Infidelity Post & System Changes

## What happened
Wrote 3 versions of a post about cheating (Детектив/УЛИКИ). All rejected by Oleg.

## Root cause chain
1. Mixed two vectors (расследование + научпоп) in one post → broken coherence
2. AI-patterns snuck in despite blacklist («это не то, что ты думаешь», «я не говорю тебе Х, я говорю Y»)
3. Two statistics in a row (74%, 42%) → overload
4. Repeated «47 исследований» in both start and body
5. Repeated «нейробиология» in start and end
6. Water sentences after 4 types («когда ты знаешь тип, ты перестаёшь гадать»)
7. Dry tool description instead of selling

## System changes made
1. **14_WRITER_FORMATION.md** — added Шаг 1.5 "Красная нить" (mandatory one-sentence promise), запреты на повторы, правила CTA (запрещено «собрала/нашла/выделила»)
2. **02_blacklist.md** — added «это не X, это Y», «я не говорю тебе Х, я говорю Y»
3. **post_analyzer.py** — +2 checks (17 total): паттерн «я не говорю Х, я говорю Y», паттерн «это не то, что ты думаешь»
4. **14_WRITER_FORMATION.md** — added правило «одна цифра на пост», запрет на повтор фактов и терминов
5. **14_WRITER_FORMATION.md** — added правило CTA: подача инструмента как уникальной разработки
6. **oleg_writing_rules_master.md** — created master file of ALL Oleg's comments on writing

## Key quote from Oleg
«Мы не просто переписываем текст — мы перестраиваем систему под то что я говорю»

## Deep research launched
- Topic: русские речевые обороты для контента — необычные, не нейросетевые
- Status: running (4 agents: DeepSeek V3, GitHub Models, Ollama, Mistral)
