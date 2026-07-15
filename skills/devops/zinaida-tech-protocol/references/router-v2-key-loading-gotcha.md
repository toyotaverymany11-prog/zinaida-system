# Система env override: ключи из systemd перекрывают .env

## Обнаружено: 11.07.2026

### Симптом
Роутер показывает 402 на DeepSeek. Прямые тесты через Python urllib — HTTP 200.
Health endpoint показывает `deepseek_key_preview: sk-2805e95...` — НЕ тот ключ что в .env.

### Корень
Systemd-сервисы (`/etc/systemd/system/zinaida-core.service.d/env.conf`) устанавливают переменные окружения через `Environment=`:

```
Environment="DEEPSEEK_API_KEY=sk-2805e95..."
```

Когда Python-скрипт делает `os.environ.setdefault("DEEPSEEK_API_KEY", val)`, он **не перезаписывает** уже существующую переменную. Если systemd установил мёртвый ключ — `setdefault()` его не заменит живым из .env.

### Диагностика
```python
# Сравнить ключи
print("из .env:", val_from_dotenv)
print("из os.environ:", os.getenv("DEEPSEEK_API_KEY"))
# Если разные — systemd перекрывает
```

Health-эндпоинт должен показывать ПЕРВЫЕ 10 СИМВОЛОВ загруженного ключа:
```python
@app.get("/health")
async def health():
    return {
        "deepseek_key_preview": DEEPSEEK_KEY[:10] + "..." if DEEPSEEK_KEY else "none",
    }
```

### Фикс
Читать API-ключи НАПРЯМУЮ из .env файла, игнорируя `os.getenv()`:

```python
DEEPSEEK_KEY = ""
for p in ["/opt/zinaida/.env", "/opt/zinaida/meta_agent/.env"]:
    if not os.path.exists(p):
        continue
    with open(p, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                val = line.split("=", 1)[1].strip()
                if val and val != "***" and len(val) > 10:
                    DEEPSEEK_KEY = val
                    break
    if DEEPSEEK_KEY:
        break
```

**Важно:** Это же относится к Mistral, Ollama, и любым другим ключам. `os.getenv()` может вернуть systemd-значение, которое отличается от .env.

### Где лежат мёртвые ключи
- `/etc/systemd/system/zinaida-core.service.d/env.conf` — мёртвый DEEPSEEK_API_KEY (401)
- `/etc/systemd/system/grigoriy.service.d/env.conf` — то же
- `/root/.bashrc` — `export DEEPSEEK_API_KEY=...` (тоже мёртвый)
- `/opt/zinaida/.env` — живой ключ (sk-f500991..., баланс $17.45)

### Связанный баг: классификатор не вызывался

Когда `model` в запросе равен "Zina2-Router" — код шёл в ветку `if requested_model` → `else: model_key = "flash"`, полностью пропуская классификатор.

**Фикс:** Любое неизвестное/общее имя модели отправлять в классификатор:
```python
if requested_model:
    req = requested_model.lower()
    if "pro" in req: model_key = "pro"
    elif "flash" in req: model_key = "flash"
    else: model_key = _classify_request(messages)  # <-- было: model_key = "flash"
```

### Короткие триггеры Pro

Слова из 2-3 символов ("api", "js", "css") не должны триггерить Pro. Обычный вопрос "Расскажи что такое API" — это Flash, не Pro.

**Фикс:** Убрать короткие триггеры (< 4 символов) из PRO_TRIGGER_WORDS.
