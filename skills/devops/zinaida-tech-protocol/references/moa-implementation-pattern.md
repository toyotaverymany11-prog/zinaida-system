# MOA (Mixture of Agents) — Implementation Pattern

## Что это
Параллельный запуск нескольких моделей LLM на один запрос. Кто ответил первым и лучше — того и берём. Вторую отменяем.

## Где внедрено (13.07.2026)
- **8005** (`router_8005_v2.py`): Mistral + gpt-4o параллельно → DeepSeek fallback
- **8003** (`zina2_router.py`): DeepSeek Flash + Pro параллельно
- **8002** (`zinaida_openai_proxy.py`): 2 провайдера из chain параллельно → победитель

## Архитектурный паттерн (Python asyncio)

```python
# 1. Создаём задачи для каждой модели
moa_task_1 = asyncio.create_task(_call_model_1(messages))
moa_task_2 = asyncio.create_task(_call_model_2(messages))

# 2. Ждём первую завершившуюся
done, pending = await asyncio.wait(
    [moa_task_1, moa_task_2],
    timeout=timeout - 2.0,
    return_when=asyncio.FIRST_COMPLETED
)

# 3. Забираем результаты
best_result = None
for task in done:
    try:
        candidate = task.result()
        if candidate and "content" in candidate:
            if not best_result or len(candidate.content) > len(best_result.content):
                best_result = candidate
    except:
        pass

# 4. Отменяем незавершённые
for task in pending:
    task.cancel()

# 5. Если MOA не дал результата — fallback
if not best_result:
    # последовательный fallback
    ...
```

## Ключевые решения

### Как выбирать победителя
- **8005**: confidence self-assessment от Mistral (≥95 → Mistral). Иначе gpt-4o.
- **8003**: длина ответа (кто длиннее → тот лучше). Flash быстрее, Pro осмысленнее.
- **8002**: первый успешный ответ (Gemini/Mistral быстрые, DeepSeek медленный).

### Таймауты
- MOA таймаут = общий timeout - 2s (чтобы осталось время на fallback)
- Для 8003: Flash обычно 1-2s, Pro 3-5s. Ждём обе до ~25s.

### Отмена задач
`task.cancel()` — корректно завершает корутины. Важно для httpx сессий (чтобы не висели открытые соединения).

## Зачем это нужно
1. **Скорость**: модель, которая ответит первой, обычно быстрее и дешевле
2. **Качество**: если быстрая модель дала мусор — медленная может дать нормальный ответ
3. **Отказоустойчивость**: если одна модель упала (timeout/429/500) — вторая подхватит
4. **Бесплатно**: Mistral + gpt-4o (GitHub) — обе бесплатные. Запуск двух бесплатных всё равно бесплатно.

## Когда НЕ использовать
- **Streaming**: MOA не работает со stream (нужно только одного провайдера и держать соединение)
- **Если одна модель явно выбрана пользователем**: модель=deepseek-reasoner → не обходить
- **Если модели используют один API-ключ**: параллельные вызовы могут превысить rate limit
