#!/usr/bin/env python3
"""
Vision Proxy: GitHub Models → Ollama Cloud (fallback)
Пробует GitHub Models (gpt-4o-mini), при ошибке → Ollama (gemma3:27b, 3 ключа)
Порт: 8901
"""
import json, aiohttp, io, base64, os, logging
from aiohttp import web
from PIL import Image

GITHUB_TOKEN = ''
MISTRAL_KEYS = []
MISTRAL_KEYS_2 = ''
OLLAMA_KEYS = []
SECRETS_PATH = "/opt/zinaida/config/secrets.env"
if os.path.exists(SECRETS_PATH):
    with open(SECRETS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "GITHUB_TOKEN":
                    GITHUB_TOKEN = v
                elif k.startswith("OLLAMA_API_KEY"):
                    OLLAMA_KEYS.append(v)
                elif k == "MISTRAL_API_KEY":
                    MISTRAL_API_KEY = v
                elif k == "MISTRAL_API_KEY_2":
                    MISTRAL_API_KEY_2 = v

OLLAMA_BASE = "https://ollama.com/v1"
GITHUB_BASE = "https://models.github.ai/inference"
PORT = 8901

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VISION-PROXY] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MAX_DIMENSION = 1024
JPEG_QUALITY = 80

def compress_image(body):
    """Сжатие PNG→JPEG, ресайз"""
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
                try:
                    header, b64_data = url.split(",", 1)
                except ValueError:
                    continue
                if len(b64_data) < 512 * 1024 and "png" not in header:
                    continue
                try:
                    img_data = base64.b64decode(b64_data)
                    img = Image.open(io.BytesIO(img_data))
                    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
                    buf = io.BytesIO()
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                    img.save(buf, "JPEG", quality=JPEG_QUALITY)
                    new_b64 = base64.b64encode(buf.getvalue()).decode()
                    content[i]["image_url"]["url"] = f"data:image/jpeg;base64,{new_b64}"
                    old_kb = len(b64_data) // 1024
                    new_kb = len(new_b64) // 1024
                    logger.info(f"Сжато: {old_kb}KB → {new_kb}KB")
                except Exception as e:
                    logger.warning(f"Ошибка сжатия: {e}")
    return body

async def proxy_vision(request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    body = compress_image(body)

    # 1. Пробуем GitHub Models
    if GITHUB_TOKEN:
        logger.info("Попытка GitHub Models...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{GITHUB_BASE}/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info("✅ GitHub Models сработал")
                        return web.json_response(data)
                    else:
                        text = await resp.text()
                        logger.warning(f"GitHub Models: {resp.status} — пробую Ollama")
        except Exception as e:
            logger.warning(f"GitHub Models ошибка: {e} — пробую Ollama")
    else:
        logger.warning("Нет GitHub токена → сразу Mistral")

    # 2. Пробуем Mistral (vision) — перебираем ВСЕ ключи при ЛЮБОЙ ошибке
    mistral_keys = [MISTRAL_API_KEY, MISTRAL_API_KEY_2]
    mistral_error = None
    for i, key in enumerate(mistral_keys):
        if not key:
            continue
        logger.info(f"Попытка Mistral (ключ {i+1})...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept-Encoding": "identity"},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✅ Mistral ключ {i+1} сработал")
                        return web.json_response(data)
                    else:
                        text = await resp.text()
                        logger.warning(f"Mistral ключ {i+1}: {resp.status} — {text[:100]}, пробую следующий")
                        mistral_error = f"Mistral key {i+1}: HTTP {resp.status}"
                        continue
        except Exception as e:
            logger.warning(f"Mistral ключ {i+1} ошибка: {e}, пробую следующий")
            mistral_error = f"Mistral key {i+1}: {e}"
            continue

    # 3. Fallback на Ollama — перебираем ВСЕ ключи при ЛЮБОЙ ошибке
    ollama_error = None
    for i, key in enumerate(OLLAMA_KEYS):
        if not key:
            continue
        logger.info(f"Попытка Ollama (ключ {i+1})...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{OLLAMA_BASE}/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✅ Ollama ключ {i+1} сработал")
                        return web.json_response(data)
                    else:
                        text = await resp.text()
                        logger.warning(f"Ollama ключ {i+1}: {resp.status} — {text[:100]}, пробую следующий")
                        ollama_error = f"Ollama key {i+1}: HTTP {resp.status}"
                        continue
        except Exception as e:
            logger.warning(f"Ollama ключ {i+1} ошибка: {e}, пробую следующий")
            ollama_error = f"Ollama key {i+1}: {e}"
            continue

    logger.error(f"Все провайдеры не сработали. Mistral: {mistral_error}, Ollama: {ollama_error}")
    return web.json_response({"error": "All vision providers failed"}, status=503)

async def health(request):
    return web.json_response({"status": "ok", "github": bool(GITHUB_TOKEN), "mistral": bool(MISTRAL_API_KEY), "ollama_keys": len(OLLAMA_KEYS)})

async def main():
    app = web.Application(client_max_size=50 * 1024 * 1024)
    app.router.add_post("/v1/chat/completions", proxy_vision)
    app.router.add_post("/chat/completions", proxy_vision)
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PORT).start()
    logger.info(f"Vision Proxy на :{PORT} — GitHub → Ollama ({len(OLLAMA_KEYS)} ключей)")
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
