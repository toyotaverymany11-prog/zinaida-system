# Vision Proxy Fallback Fix — 2026-07-09

## Проблема

Оба vision прокси (порт 8900 и 8901) при ошибке от провайдера (кроме 401)
возвращали HTTP 500 клиенту, не пробуя следующие ключи/провайдеры.

### `vision_fallback_proxy.py` (порт 8901)

**Цепочка:** GitHub → Mistral (2 ключа) → Ollama (3 ключа)

Баг: при `resp.status != 200` и `resp.status != 401` — immediate return.
```python
else:
    text = await resp.text()
    logger.error(f"Mistral {resp.status}: {text[:100]}")
    return web.json_response({"error": f"Mistral error {resp.status}"}, status=resp.status)
```
То же самое для Ollama. Если Mistral вернул 400 (Bad Request) — сразу 500.

**Фикс:** перебор всех ключей при ЛЮБОЙ ошибке. Только когда все исчерпаны — 503.

### `ollama_fallback_proxy.py` (порт 8900)

**Цепочка:** Ollama (3 ключа)

Тот же баг: `resp.status != 200` → immediate return.
Фикс: перебор всех ключей при ЛЮБОЙ ошибке.

### Симптом для пользователя

Ошибка в браузере Hermes Studio:
```
HTTP 500 — {'error': "Mistral error 400"}
```

## Что было сделано

1. В `vision_fallback_proxy.py`:
   - Убрала `elif resp.status == 401: continue`
   - Заменила `else: return web.json_response(...)` на `else: continue` для обоих провайдеров (Mistral, Ollama)
   - Добавила переменные `mistral_error` / `ollama_error` для логирования последней ошибки
   - При 503 возвращается `"All vision providers failed"` с последней ошибкой в логе

2. В `ollama_fallback_proxy.py`:
   - Заменила `return web.json_response(...)` на `continue` при `resp.status != 200`
   - `last_error` накапливает последний статус

3. Перезапущена:
   - `kill <pid>` + background запуск обоих прокси (через `ps aux | grep` — lsof не установлен на сервере)

## Проверка

```bash
curl -s http://127.0.0.1:8900/health    # {"status":"ok","keys":3}
curl -s http://127.0.0.1:8901/health    # {"status":"ok","github":true,"mistral":true,"ollama_keys":3}
```

## Файлы

- `/opt/zinaida/scripts/vision_fallback_proxy.py`
- `/opt/zinaida/scripts/ollama_fallback_proxy.py`
