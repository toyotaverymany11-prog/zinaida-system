# Пунктуационный фильтр — роутеры уровня 8002 и 8003

## Проблема
DeepSeek / Mistral стабильно ставят длинные тире (—) в тексте. 
Никакие промпты не решают проблему полностью — LLM слишком привыкла к типографике.

## Решение 11.07.2026
Добавлены автоматические фильтры на уровне SSE-чанков (стрим) и JSON-ответов (не-стрим):

### zinaida_openai_proxy.py (порт 8002)

**Функция `_sanitize_chunk_content()`** — вызывается внутри `_strip_reasoning_from_chunk()`:
```python
def _sanitize_chunk_content(data: dict) -> dict:
    for ch in data.get("choices", []):
        delta = ch.get("delta", {})
        content = delta.get("content")
        if content:
            content = content.replace("\u2014", "-").replace("\u2013", "-")
            content = content.replace("\u2026", ".")
            for bullet in ["\u2022", "\u25CF", "\u25E6"]:
                content = content.replace(bullet, "-")
            delta["content"] = content
    return data
```

**Функция `_strip_reasoning_from_response()`** — обновлена для не-стрим пути: то же замены.

### zina2_router.py (порт 8003)

**Функция `_sanitize_sse_chunk()`** — аналогичная, для DeepSeek стрим-чанков + message-ответов.
**Функция `_sanitize_response_json()`** — для не-стрим пути.

### CORE.md (system prompt роутера 8002)

Добавлен раздел "ПУНКТУАЦИЯ — ЖЁСТКИЙ ЗАПРЕТ":
```
ЗАПРЕЩЕНО использовать в тексте:
- Длинное тире «—» (заменять на обычный дефис «-»)
- Среднее тире «–» (заменять на дефис «-»)
- Многоточие в конце предложения (заменять на точку)
- Жирные точки «• ● ◦» (заменять на дефис или двоеточие)
- Длинное тире в смысле «— это» (заменять на «- это» или «это»)
```

### blacklist_patterns.json

Добавлены 6 символов:
```
"—", "–", "…", "•", "●", "◦"
```
Всего: 29 записей (было 26).

## Что чинить если проблема вернётся

1. Проверить что роутеры перезапущены:
   `curl -s http://127.0.0.1:8002/v1/models` → 200
   `curl -s http://127.0.0.1:8003/v1/models` → 200

2. Проверить работает ли фильтр на уровне роутера:
   `grep -n "_sanitize_chunk_content\|_sanitize_sse_chunk\|_sanitize_response_json" /opt/zinaida/meta_agent/zinaida_openai_proxy.py /opt/zinaida/meta_agent/zina2_router.py`

3. Если фильтр есть, но длинные тире всё равно проходят — проблема может быть в пути вызова: стрим-генератор мог не обернуться в фильтр. Проверить `winner_stream` и `fallback_stream` в обоих роутерах.

4. Если проблема на уровне Hermes Studio а не роутера (например, Web UI сам подставляет типографику) — смотреть `display.show_reasoning` и html-rendering.
