# Reasoning и отображение модели — исправления 2026-07-10

## Проблема 1: Блок «Процесс размышления» на английском в чате

**Симптом:** В Hermes Web UI перед ответом Зинаиды показывается блок «Процесс размышления · N зн.» на английском. Олег в ярости.

**Корень:** Два независимых источника:

### Уровень 1: Hermes config — `show_reasoning`
Файл: `/root/.hermes/config.yaml`
```yaml
display:
  show_reasoning: false   # было true
```
Перезагрузить gateway после изменения: `systemctl restart hermes-gateway.service`

### Уровень 2: Модель возвращает `reasoning_content` в API-ответе
DeepSeek (и другие reasoning-модели) возвращают поле `reasoning_content` в SSE-чанках. Hermes Web UI рендерит его как «Процесс размышления». Если config не помогает — значит модель возвращает reasoning_content на уровне API, и его надо вырезать в роутере.

**Фикс:** Добавить в роутер (zinaida_openai_proxy.py) функцию очистки reasoning из ответов модели:

```python
def _strip_reasoning_from_chunk(chunk: str):
    """Удаляет reasoning_content/reasoning из SSE-чанка.
    Если после удаления в дельте пусто — возвращает None (пропускаем чанк)."""
    if chunk == "data: [DONE]":
        return chunk
    try:
        data = json.loads(chunk[6:])
        for ch in data.get("choices", []):
            delta = ch.get("delta", {})
            removed = delta.pop("reasoning_content", None) or delta.pop("reasoning", None)
            if removed is not None and not delta.get("content"):
                return None
        return "data: " + json.dumps(data, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, IndexError):
        return chunk

def _strip_reasoning_from_response(result: dict) -> dict:
    """Удаляет reasoning из не-streaming ответа."""
    for ch in result.get("choices", []):
        msg = ch.get("message", {})
        msg.pop("reasoning", None)
        msg.pop("reasoning_content", None)
    return result
```

Применить к стриминговым генераторам (winner_stream, fallback_stream) и не-стрим пути (перед JSONResponse).

### Проверка
1. `grep "show_reasoning" /root/.hermes/config.yaml` → должно быть `false`
2. Отправить тестовый запрос — нет блока «Процесс размышления»
3. Если в новом чате (после /reset) всё чисто — фикс сработал

---

## Проблема 2: В выпадайке модели «Zinaida-Router», в чате показывает другое

**Симптом:** Олег выбирает в Web UI модель «Zinaida-Router», а в чате/футере отображается «Zina2-Router» или «gpt-4o» или каша.

**Корень:** В конфиге Hermes у модели Zinaida-Router было `model: ' gpt-4o'` (с ПРОБЕЛОМ в начале). Из-за этого:
- В Web UI выпадайка показывает «Zinaida-Router» (поле name)
- Внутри Hermes шлёт ` model` = ` gpt-4o` в роутер
- Роутер на 8002 игнорирует model name (у него свой выбор), но в сессии Hermes фиксируется имя с пробелом
- При переключении между роутерами (8002 vs 8003) отображение путается

**Фикс:**
```bash
sed -i "s/model: ' gpt-4o'/model: Zinaida-Router/" /root/.hermes/config.yaml
systemctl restart hermes-gateway.service
```

**Проверка:** В выпадайке оба варианта: «Zinaida-Router» (8002) и «Zina2-Router» (8003). В чате отображается то, что выбрано.

---

## Два роутера на сервере — памятка

| Имя | Порт | Что внутри | Ключи | Статус |
|-----|------|-----------|-------|--------|
| Zinaida-Router | 8002 | 7 провайдеров (Mistral→GigaChat→DeepSeek) | Есть проблемы | Используется редко |
| Zina2-Router | 8003 | DeepSeek Flash/Pro/V3 (автовыбор) | DeepSeek API ключ | ОСНОВНОЙ |

Default в config.yaml: Zina2-Router (потому что DeepSeek Pro лучше для контента, не цензурирует).
