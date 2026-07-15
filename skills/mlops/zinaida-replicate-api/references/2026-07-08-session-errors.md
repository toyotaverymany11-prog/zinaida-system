# Сессия 2026-07-08: Replicate API проблемы и решения

## Проблема 1: FileOutput object has no attribute 'type'

**Симптом:** `replicate.run(MODEL, input={...})` падает с `'FileOutput' object has no attribute 'type'`.

**Причина:** replicate Python библиотека (v0.x) возвращает объект `FileOutput`, у которого есть `.url` но нет `.type`. Если код пытается сделать `output[0]` (индексация как список), Python пытается получить `__getitem__`, что внутри библиотеки делает `type()` проверку — падает.

**Провалился:** даже код с `if hasattr(output, 'url'): url = output.url` не срабатывал, потому что библиотека перехватывает атрибуты.

**Рабочее решение:** urllib через REST API.

## Проблема 2: Prefer: wait возвращает пустой output

**Симптом:** prediction создан, статус "starting" или "processing", output=None.

**Причина:** `Prefer: wait` header говорит API ждать до 60 секунд. Если за 60 секунд модель не успела — возвращается промежуточный статус без output.

**Решение:** не использовать Prefer: wait. Создать prediction → получить ID → polling раз в 5 секунд.

## Проблема 3: Rate Limits (429)

**Симптом:** после 2-3 успешных запросов — HTTP 429.

**Лимиты:** ~6 prediction/запросов в минуту (очень строго).

**Решение:** `time.sleep(10)` между запросами. При 429 — `time.sleep(60)` и retry.

## Проблема 4: Токен под маскировкой Hermes

**Симптом:** в коде `python3 -c "..."` токен выглядит как `***`, и код буквально использует строку с `***`.

**Причина:** Hermes маскирует секреты ДАЖЕ внутри кода, который ты пишешь. Если ты скопировал `r8_QZWT...5eXs` из вывода терминала, то в твой код попала строка с `***` вместо реального токена.

**Решение:** всегда читать токен из файла:
```python
tok = ''
with open('/opt/zinaida/config/secrets.env') as f:
    for line in f:
        if 'REPLICATE_API_TOKEN' in line:
            tok = line.strip().split('=', 1)[1]
            break
```
Или использовать готовые скрипты.
