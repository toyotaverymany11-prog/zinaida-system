#!/usr/bin/env python3
"""
Ollama Fallback Proxy — перебирает ключи при 401 ошибке.
Прокси для Hermes vision: если один ключ протух, автоматом пробует следующий.

Порядок: OLLAMA_API_KEY_1 → OLLAMA_API_KEY_2 → OLLAMA_API_KEY_3
Если все три 401 — возвращает ошибку.

Запуск: python3 /opt/zinaida/scripts/ollama_fallback_proxy.py
Порт: 8900
"""

import asyncio
import json
import os
import sys
import logging

import aiohttp
from aiohttp import web

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/v1")
PORT = int(os.getenv("PROXY_PORT", "8900"))

# === Читаем ключи из secrets.env ===
SECRETS_PATH = "/opt/zinaida/config/secrets.env"

def load_secrets():
    keys = {}
    if os.path.exists(SECRETS_PATH):
        with open(SECRETS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    keys[k.strip()] = v.strip()
    return keys

_secrets = load_secrets()

KEYS = [
    _secrets.get("OLLAMA_API_KEY_1"),
    _secrets.get("OLLAMA_API_KEY_2"),
    _secrets.get("OLLAMA_API_KEY_3"),
]

# Отсекаем пустые
KEYS = [k for k in KEYS if k]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OLLAMA-PROXY] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 512 * 1024  # 512KB макс размер base64
JPEG_QUALITY = 80
MAX_DIMENSION = 1024

def process_images_sync(body):
    """Ресайз и конвертация PNG→JPEG для vision запросов.
    Модифицирует body на месте."""
    messages = body.get("messages", [])
    for msg in messages:
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for i, part in enumerate(content):
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                if not url or not url.startswith("data:image"):
                    continue

                # Декодируем
                try:
                    header, b64_data = url.split(",", 1)
                except ValueError:
                    continue

                # Если размер в пределах нормы — не трогаем
                if len(b64_data) < MAX_IMAGE_SIZE and "png" not in header:
                    continue

                # Конвертируем
                try:
                    import base64, io
                    from PIL import Image

                    img_data = base64.b64decode(b64_data)
                    img = Image.open(io.BytesIO(img_data))

                    # Ресайз если слишком большое
                    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

                    # Конвертируем в JPEG
                    buf = io.BytesIO()
                    # Если есть альфа-канал, конвертируем в RGB
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                    img.save(buf, "JPEG", quality=JPEG_QUALITY)
                    new_b64 = base64.b64encode(buf.getvalue()).decode()

                    # Обновляем URL
                    new_header = "data:image/jpeg;base64"
                    content[i]["image_url"]["url"] = f"{new_header},{new_b64}"

                    old_size = len(b64_data)
                    new_size = len(new_b64)
                    ratio = (1 - new_size / old_size) * 100
                    logger.info(f"Изображение сжато: {old_size//1024}KB → {new_size//1024}KB ({ratio:.0f}%)")
                except Exception as e:
                    logger.warning(f"Не удалось обработать изображение: {e}")

    return body

async def proxy_vision(request):
    """Принимает запрос от Hermes, пробует ключи по порядку, возвращает ответ Ollama.
    Автоматически ресайзит большие изображения и конвертирует PNG→JPEG."""
    try:
        body_text = await request.text()
        logger.info(f"Получен запрос: {len(body_text)} байт, первые 100: {body_text[:100]}")
        body = json.loads(body_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return web.json_response({"error": "invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Body read error: {e}")
        return web.json_response({"error": str(e)}, status=400)

    # Обработка изображений в запросе
    body = process_images_sync(body)

    # Пробуем каждый ключ
    last_error = None
    for i, api_key in enumerate(KEYS):
        if not api_key:
            continue

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        target_url = f"{OLLAMA_BASE}/chat/completions"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    target_url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 401:
                        text = await resp.text()
                        logger.warning(f"Ключ {i+1} — 401, пробую следующий")
                        last_error = f"Key {i+1}: 401"
                        continue

                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(f"Ключ {i+1}: {resp.status} — {text[:200]}, пробую следующий")
                        last_error = f"Key {i+1}: HTTP {resp.status}"
                        continue

                    # Успех — возвращаем ответ как есть
                    data = await resp.json()
                    logger.info(f"✅ Ключ {i+1} сработал, модель: {body.get('model', '?')}")
                    return web.json_response(data)

        except asyncio.TimeoutError:
            logger.warning(f"Ключ {i+1} — таймаут, пробую следующий")
            last_error = f"Key {i+1}: timeout"
            continue
        except aiohttp.ClientError as e:
            logger.warning(f"Ключ {i+1} — ошибка соединения: {e}, пробую следующий")
            last_error = f"Key {i+1}: {e}"
            continue

    # Все ключи не сработали
    logger.error(f"Все ключи не сработали. Последняя ошибка: {last_error}")
    return web.json_response(
        {"error": f"All keys failed: {last_error}"},
        status=503
    )


async def health(request):
    return web.json_response({"status": "ok", "keys": len(KEYS)})


async def main():
    app = web.Application(client_max_size=50 * 1024 * 1024)  # 50MB лимит
    app.router.add_post("/v1/chat/completions", proxy_vision)
    app.router.add_post("/chat/completions", proxy_vision)
    app.router.add_get("/health", health)
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", PORT)
    await site.start()
    logger.info(f"🚀 Ollama Fallback Proxy запущен на порту {PORT}")
    logger.info(f"🔑 Загружено ключей: {len([k for k in KEYS if k])}")
    logger.info(f"🌐 Целевой URL: {OLLAMA_BASE}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлен")
