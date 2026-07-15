# Single DeepSeek Call Pattern (реализован 11.07.2026)

## Проблема
Раньше RAG и DeepSeek запускались параллельно:
1. DeepSeek без контекста → ответ
2. RAG готов → перегенерация с контекстом
= 2 вызова DeepSeek, двойная цена, двойное время

## Фикс: RAG сначала → 1 вызов

```python
# 1. RAG сначала (0.05-3 сек)
rag_chunks = await _search_rag(last_user)

# 2. Контекст в последнее сообщение пользователя
if rag_chunks:
    for m in reversed(messages):
        if m["role"] == "user":
            m["content"] = f"{m['content']}\n\n---\nКонтекст с сервера:\n{rag_chunks}"
            break

# 3. ОДИН вызов DeepSeek
result = await _call_deepseek(model_id, payload_with_context)
```

## Важно
- Контекст добавляется в последнее сообщение пользователя, не отдельным system-сообщением
- DeepSeek получает контекст сразу, не нужно перегенерировать
- Mistral analyzer запускается после DeepSeek, параллельно — не блокирует ответ
- Если RAG ничего не нашёл (меньше 50 символов) — контекст не добавляется, вызов как обычно

## Экономия
- Было: 2 вызова DeepSeek (~$0.00054 за Flash)
- Стало: 1 вызов (~$0.00027)
+ вдвое быстрее суммарно
