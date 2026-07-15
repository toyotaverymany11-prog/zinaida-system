# Script Verification Report — 12.07.2026

## Проверка: post_architect.py и compile_writer_context.py

### Статус: ✅ ОБА РАБОТАЮТ

Проверено 12.07.2026 в сессии «Писатель 3». Скрипты живы, выдают корректные результаты.

---

## post_architect.py

**Путь:** `/opt/zinaida/scripts/post_architect.py`

**Команда:**
```bash
cd /opt/zinaida/scripts && python3 post_architect.py --theme "молчит" --platform "VK"
```

**Результат:** ✅ 0 ошибок, exit code 0, время выполнения ~0.5 сек
- Выдаёт: фазу (Г1), инструмент (Детектив → Телепат), метафору, CTA с ключевым словом, open loop
- Сохраняет в `/opt/zinaida/memory/post_architecture_latest.txt`

**Что проверить:** stdout содержит блоки: ФАЗА, ХУК, TEASER, МЕТАФОРА, ФОРМАТ, ИНСТРУМЕНТ, CTA, OPEN LOOP, ПРОВЕРКИ

---

## compile_writer_context.py

**Путь:** `/opt/zinaida/scripts/compile_writer_context.py`

**Команда (ВАЖНО: повышенный таймаут):**
```bash
cd /opt/zinaida/scripts && timeout 90 python3 compile_writer_context.py --theme "молчит" --platform "VK"
```

**Результат:** ✅ 0 ошибок, exit code 0, время выполнения ~15-20 сек
- Шлёт запросы в роутер 8002 (Mistral) для RAG и анализа
- Выдаёт 11 блоков: фазы, статистика, хуки, CTA, RAG, алгоспик, чёрный список
- Сохраняет в `/opt/zinaida/memory/writer_context_latest.txt`

**⚠️ ВАЖНО — ТАЙМАУТ (источник ошибок прошлых сессий):**
- При дефолтном timeout=30s в terminal() скрипт падает — не успевает получить ответ от роутера 8002
- Всегда запускать с `timeout=90` или выше
- Скрипт идемпотентен — можно запустить снова без последствий
- Если падает с ошибкой связи с роутером — проверь `curl http://127.0.0.1:8002/v1/models` (должен быть 200)

**Что проверить в stdout:** должен содержать блоки:
```
БЛОК 1: СТИЛЬ ШКВАЛЬНЫЙ (16 ПРАВИЛ)
БЛОК 2: ФАЗЫ (phases.db)
БЛОК 3: СТАТИСТИКА
БЛОК 4: ЧЁРНЫЙ СПИСОК
БЛОК 5: ХУКИ ИЗ БАЗЫ
БЛОК 6: CTA ИЗ БАЗЫ
БЛОК 7: RAG КОНТЕКСТ
БЛОК 8: ПЛАТФОРМА
БЛОК 9: CTA-ВОРОНКА
БЛОК 10: АЛГОСПИК
БЛОК 11: ЧЁРНЫЙ СПИСОК JSON
```

---

## post_analyzer.py

**Путь:** `/opt/zinaida/scripts/post_analyzer.py`

**Команда:**
```bash
python3 /opt/zinaida/scripts/post_analyzer.py "текст поста"
```

**Статус:** ✅ Работает. Проверяет 17 пунктов: тире, многоточия, AI-паттерны, чёрный список, запрещённые CTA-фразы.

---

## Почему скрипты «не срабатывали» раньше — 3 корневые причины

1. **Таймаут compile_writer_context.py.** Основная причина. Скрипту нужно 60-90s из-за запросов к роутеру 8002. При дефолтном 30s terminal() таймауте — тихо падает.

2. **Нет привычки запускать.** В архитектуре писателя прописано «запустить оба скрипта перед генерацией», но я часто шла сразу в LLM без них.

3. **Путаница в структуре папок.** Часть файлов в `inbox/PROJECTS/Otnoshenya/`, часть в `projects/Otnoshenya/pisatel/`. `search_files` искала в `inbox/` и не находила.

---

## Быстрая проверка скриптов (health check)

```bash
# Проверить что файлы существуют
ls -la /opt/zinaida/scripts/post_architect.py /opt/zinaida/scripts/compile_writer_context.py

# Проверить что роутер жив (нужен compile_writer_context.py)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/v1/models
# Должно быть: 200

# Быстрый запуск post_architect (0.5 сек, без зависимостей)
python3 /opt/zinaida/scripts/post_architect.py --theme "молчит" --platform "VK" 2>&1 | head -5
```
