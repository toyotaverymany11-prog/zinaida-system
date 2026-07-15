# Proxy Vision Fix — 2026-07-08

## Проблема
vision_analyze падал с 400 на больших PNG (>1MB base64). Две причины:

### 1. aiohttp client_max_size (по умолчанию ~1MB)
Запрос с base64 PNG весит >1MB. aiohttp отклоняет до чтения body.
**Фикс:** `web.Application(client_max_size=50 * 1024 * 1024)` в `main()` прокси.

### 2. Gemma3:27b не принимает PNG больше 512KB base64
Ollama Cloud возвращает `400 {"error": "invalid JSON"}`.
**Фикс:** функция `process_images_sync()` в прокси, которая:
- Проверяет размер base64: если >512KB ИЛИ PNG → конвертирует
- Декодирует, открывает через PIL, ресайзит до 1024px
- Конвертирует в JPEG (quality=80), заменяет URL в body
- Логирует сжатие: "Изображение сжато: NKB → MKB (X%)"

## Архитектура фикса
process_images_sync(body) вызывается синхронно внутри proxy_vision (async), ДО передачи запроса в Ollama. Не использовать `asyncio.to_thread()` — он не сработал, функция заменила body но JSON полетел. Прямой синхронный вызов работает.

## Код (кратко)
```python
MAX_IMAGE_SIZE = 512 * 1024  # 512KB
JPEG_QUALITY = 80
MAX_DIMENSION = 1024

def process_images_sync(body):
    for msg in body.get("messages", []):
        content = msg.get("content", [])
        if not isinstance(content, list): continue
        for i, part in enumerate(content):
            if not isinstance(part, dict) or part.get("type") != "image_url": continue
            url = part.get("image_url", {}).get("url", "")
            if not url or not url.startswith("data:image"): continue
            try: header, b64_data = url.split(",", 1)
            except ValueError: continue
            if len(b64_data) < MAX_IMAGE_SIZE and "png" not in header: continue
            # Convert: PIL → JPEG → replace url
            ...
```

## Проверка после фикса
- `vision_analyze` на PNG 1320x2868 (824KB) → ✅ success
- Прямой вызов через urllib → ✅ success
- Принудительный сброс прокси: `systemctl restart ollama-proxy.service`
