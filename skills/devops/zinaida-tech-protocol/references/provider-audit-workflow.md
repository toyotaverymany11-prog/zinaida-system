# Провайдер-аудит: систематическая проверка API-ключей

## Когда применять
- При подозрении на протухшие ключи (Олег пишет «все ключи протухли»)
- После обновления какого-либо ключа
- После миграции сервера
- На регулярной основе (раз в 2 недели)

## Протокол

### 1. Сбор ключей
```bash
# Читаем ВСЕ .env файлы в проекте
grep -rh "API_KEY\|TOKEN\|SECRET" /opt/zinaida/.env /opt/zinaida/meta_agent/.env /root/.hermes/.env 2>/dev/null | sort -u
```

### 2. Написать тестовый скрипт
Создать скрипт `/opt/zinaida/sandbox/test_all_providers.py` со структурой:

```python
def test_provider(name, url, headers, data=None):
    """Универсальная функция теста. Возвращает строку с результатом."""
    try:
        req = urllib.request.Request(url, data=data, headers=headers, ...)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return f"✅ {name}: HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return f"❌ {name}: HTTP {e.code} — {body}"
    except Exception as e:
        return f"❌ {name}: {str(e)[:150]}"
```

### 3. Что тестировать (всегда 3 уровня)
1. **Прямые API** — Mistral, Ollama, GitHub Models, DeepSeek, OpenRouter
2. **Локальные роутеры** — Zina2-Router (8003), Zinaida-Router (8002)
3. **Проверка моделей** — не только `/models` но и `/chat/completions` с реальным запросом

### 4. Важно: маскировка ключей
Система маскирует секреты в выводе `***`. Это НЕ значит что ключ не работает.
- Если curl вернул `HTTP 200`, значит ключ РАБОТАЕТ. Маскировка только визуальная.
- Для проверки в Python: читать `.env` через `open(path, 'rb')` и извлекать значение.
- Если нужно записать ключ в конфиг — писать Python-скриптом, а не вручную (маскировка помешает).

### 5. Фиксация результатов
После аудита — записать в `/opt/zinaida/shared_memory/updates_log.md`:
```markdown
## 2026-07-11 Аудит провайдеров
- Mistral: ✅ 3/4 (1 протух)
- GitHub Models: ❌ 401 - токен протух
- DeepSeek: ❌ 401 - ключ протух
- Ollama: ✅ 3/3
- Zina2-Router (8003): ✅
- Zinaida-Router (8002): ✅
```

Также обновить провайдер-таблицу в навыке `zinaida-tech-protocol`.

### 6. Если ключи не работают — что предлагать
| Симптом | Что делать |
|---------|-----------|
| 401 Unauthorized | Ключ протух. Нужен новый. |
| 403 Forbidden | IP заблокирован. Нужен прокси или новый IP. |
| 400 Bad Request | Формат запроса неверный или ключ не подходит. |
| Таймаут | Сервер недоступен из РФ (блокировка). |

### 7. Рабочий стек (проверено 11.07.2026)
```
Zina2-Router (8003) — DeepSeek V4 Flash
  └→ fallback Zinaida-Router (8002) — Mistral
  └→ fallback Mistral direct — 3 ключа
  └→ Ollama Cloud — 3 ключа (gemma3:4b бесплатно)
  
НЕ РАБОТАЮТ: GitHub Models, GitHub Copilot, DeepSeek direct, Nous Portal (все протухли/заблокированы)
```
