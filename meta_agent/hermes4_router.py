#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 HERMES 8003 ROUTER v1.0 — трёхуровневый каскад Hermes-4
================================================================================
Порт: 8003 (заменил Zina2-Router с DeepSeek)

Три модели Nous Portal Hermes-4:
  1) hermes-4-8b   — мелкие запросы (привет/ок/да/нет)      ($0.04/М токенов)
  2) hermes-4-70b  — обычные запросы (анализ/ответы/помощь)  ($0.13/М токенов)
  3) hermes-4-405b — сложные (код/стратегия/креатив)         ($1.00/М токенов)

Классификатор сам решает какую модель включить.
Все запросы идут через Nous Portal Inference API.

API: https://inference-api.nousresearch.com/v1
Ключ: из секретов (NOUS_PORTAL_KEY)
================================================================================
"""

import sys, os, json, time, uuid, logging, asyncio, warnings, copy
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import httpx

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HERMES3] %(message)s")
logger = logging.getLogger("hermes3_router")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Hermes-4 Router v1.0")

# ============================================================================
# 1. КОНФИГУРАЦИЯ — ключ и API
# ============================================================================
def load_key():
    """Ищем ключ во всех .env файлах и os.environ"""
    # Сначала os.environ
    val = os.environ.get("NOUS_PORTAL_KEY", "")
    if val and val.startswith("sk-nous"):
        return val

    # Потом файлы
    search_paths = [
        "/opt/zinaida/.env.nous_key",
        "/root/.hermes/secrets.env",
        "/root/.hermes/.env",
        "/opt/zinaida/.env.nous",
        "/opt/zinaida/.env",
        "/opt/zinaida/meta_agent/.env",
    ]
    for env_path in map(Path, search_paths):
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "NOUS_PORTAL_KEY" in line or "sk-nous" in line:
                        if "=" in line:
                            val = line.split("=", 1)[1].strip().strip("\"'")
                            if val.startswith("sk-nous"):
                                return val
    return ""

with open("/opt/zinaida/.env.nous_key") as _key_f:
    NOUS_KEY = _key_f.read().strip()
if not NOUS_KEY:
    NOUS_KEY = os.environ.get("NOUS_PORTAL_KEY", "")
if not NOUS_KEY:
    logger.error("!!! NOUS_PORTAL_KEY не найден ни в одном .env !!!")
else:
    logger.info("NOUS_PORTAL_KEY загружен: длина=%d", len(NOUS_KEY))

NOUS_API_URL = "https://inference-api.nousresearch.com/v1/chat/completions"

# Пороги для классификации
SMALL_CHAR_THRESHOLD = int(os.getenv("HERMES_SMALL_CHAR", "10"))    # <= 30 символов → 8B
BIG_CHAR_THRESHOLD   = int(os.getenv("HERMES_BIG_CHAR", "200"))     # > 300 символов → 405B
TIMEOUT              = float(os.getenv("HERMES_TIMEOUT", "180.0"))
CONNECT_TIMEOUT      = float(os.getenv("HERMES_CONNECT_TIMEOUT", "4.0"))

# ============================================================================
# 2. ТРИ МОДЕЛИ Hermes-4
# ============================================================================
MODELS = {
    "small": {
        "id": "nousresearch/hermes-4-70b",
        "name": "Hermes-4-70B (обычный)",
        "cost_per_m": 0.04,
    },
    "medium": {
        "id": "nousresearch/hermes-4-70b",
        "name": "Hermes-4-70B (средний)",
        "cost_per_m": 0.13,
    },
    "big": {
        "id": "nousresearch/hermes-4-405b",
        "name": "Hermes-4-405B (мощный)",
        "cost_per_m": 1.00,
    },
}

ALLOWED_KEYS = {"model", "messages", "stream", "max_tokens", "temperature", "top_p",
                "frequency_penalty", "presence_penalty", "stop", "user", "tools",
                "tool_choice", "parallel_tool_calls", "response_format"}

# Лимиты параметров — Nous Portal не принимает больше
MAX_TOKENS_LIMIT = 8192  # Nous Portal: макс 131072 всего, оставляем 8192 на генерацию

# ============================================================================
# 3. КЛАССИФИКАТОР — small / medium / big
# ============================================================================
# Простые слова — immediate small
SMALL_ONLY_WORDS = {"привет", "прив", "здравствуй", "пока", "да", "нет", "ок", "окей", "ладно",
                    "ага", "спасибо", "понял", "поняла", "хорошо", "норм",
                    "здравствуй", "прив", "hi", "hello", "ok", "yes", "no"}

# Триггеры для big (405B) — только если реально сложно
BIG_TRIGGER_WORDS = {
    # Стратегия/архитектура
    "стратегия", "архитектура", "архитектурный", "проектируй", "спроектируй",
    "сложный", "сложно", "оптимизация", "оптимизируй", "производительность",
    "высоконагруженный", "распределённый", "микросервисный",
    # Код/разработка
    "рефакторинг", "деплой", "миграция", "архитектура бд", "инфраструктура",
    "асинхронный", "многопоточный", "алгоритм", "сложный код",
    "бенчмарк", "профилирование", "кэширование",
    # Глубокий анализ
    "глубокий анализ", "глубокое исследование", "разбери по полочкам",
    "фундаментальный", "научный", "исследование", "диссертация",
    "сравнительный анализ", "причинно-следственный",
    # Общие триггеры для 405B
    "обоснуй", "докажи", "аргументируй", "верифицируй",
    "предскажи", "спрогнозируй", "смоделируй",
}

def _classify(messages: List[dict], requested_model: str = "") -> str:
    """Выбирает модель: small, medium или big."""
    req = requested_model.lower()

    # Явный запрос конкретной модели
    if "405b" in req or "big" in req:
        logger.info("CLASSIFY: big (явный запрос)")
        return "big"
    if "70b" in req or "medium" in req:
        logger.info("CLASSIFY: medium (явный запрос)")
        return "medium"
    if "8b" in req or "small" in req:
        logger.info("CLASSIFY: small (явный запрос)")
        return "medium"

    if not messages:
        return "medium"

    # Берём последнее сообщение пользователя
    last_user = None
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break

    if not last_user:
        return "medium"

    text_lower = last_user.lower()
    words = text_lower.split()

    # 1. Одно-два слова из SMALL_ONLY → medium (70B)
    if len(words) <= 2 and all(w.strip(".,!?") in SMALL_ONLY_WORDS for w in words):
        logger.info("CLASSIFY: medium (приветствие/односложно)")
        return "medium"

    # 2. Длина > BIG_CHAR_THRESHOLD → big (405B)
    if len(last_user) > BIG_CHAR_THRESHOLD:
        logger.info("CLASSIFY: big (длина=%d > %d)", len(last_user), BIG_CHAR_THRESHOLD)
        return "big"

    # 3. Есть триггер-слово для big → big (405B)
    for word in BIG_TRIGGER_WORDS:
        if word in text_lower:
            logger.info("CLASSIFY: big (триггер '%s')", word)
            return "big"

    # 4. Длина > SMALL_CHAR_THRESHOLD или есть содержательные слова → medium (70B)
    if len(last_user) > SMALL_CHAR_THRESHOLD or any(
        w not in SMALL_ONLY_WORDS for w in words
    ):
        logger.info("CLASSIFY: medium (содержательный запрос)")
        return "medium"

    # 5. Всё остальное → medium (70B) — безопасный выбор
    logger.info("CLASSIFY: medium (по умолчанию)")
    return "medium"

# ============================================================================
# 4. ВЫЗОВ NOUS INFERENCE API
# ============================================================================
async def _call_nous(model_id: str, payload: dict, timeout: float) -> dict:
    headers = {
        "Authorization": f"Bearer {NOUS_KEY}",
        "Content-Type": "application/json",
    }
    work = copy.deepcopy(payload)
    work["model"] = model_id

    async with httpx.AsyncClient(verify=False,
            timeout=httpx.Timeout(timeout, read=timeout, connect=CONNECT_TIMEOUT)) as client:
        resp = await client.post(NOUS_API_URL, headers=headers, json=work)
        if resp.status_code >= 400:
            err_text = resp.text[:300]
            logger.warning("Nous HTTP %d: %s", resp.status_code, err_text)
        resp.raise_for_status()
        return resp.json()

async def _call_nous_stream(model_id: str, payload: dict, timeout: float):
    headers = {
        "Authorization": f"Bearer {NOUS_KEY}",
        "Content-Type": "application/json",
    }
    work = copy.deepcopy(payload)
    work["model"] = model_id
    work["stream"] = True

    client = httpx.AsyncClient(verify=False,
            timeout=httpx.Timeout(timeout, read=timeout, connect=CONNECT_TIMEOUT))
    try:
        resp = await client.send(
            client.build_request("POST", NOUS_API_URL, headers=headers, json=work),
            stream=True)
        if resp.status_code >= 400:
            err_text = await resp.aread()
            await resp.aclose()
            await client.aclose()
            raise Exception(f"HTTP {resp.status_code}: {err_text.decode()[:200]}")
        return client, resp
    except Exception:
        await client.aclose()
        raise

# ============================================================================
# 5. SANITIZE
# ============================================================================
def sanitize_payload(payload: dict) -> dict:
    cleaned = {k: v for k, v in payload.items() if k in ALLOWED_KEYS}
    # Ограничиваем max_tokens
    if "max_tokens" in cleaned:
        cleaned["max_tokens"] = min(int(cleaned["max_tokens"]), MAX_TOKENS_LIMIT)
    else:
        cleaned["max_tokens"] = MAX_TOKENS_LIMIT
    return cleaned

def _fallback_text() -> str:
    return ("Hermes-4 временно недоступен. Попробуй позже — автовосстановление запущено.")

def _fallback_response():
    return {
        "id": "chatcmpl-fallback", "object": "chat.completion",
        "created": int(time.time()), "model": "Hermes-4-Router",
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": _fallback_text()},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

# ============================================================================
# 6. ЭНДПОИНТЫ
# ============================================================================
@app.post("/v1/chat/completions")
async def chat(request: Request):
    try:
        data = await request.json()
        is_stream = data.get("stream", False)
        timeout = float(data.get("timeout", TIMEOUT))
        messages = data.get("messages", [])

        # Дата
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if messages and messages[0].get("role") == "system":
            if "[СЕГОДНЯ:" not in messages[0]["content"]:
                messages[0]["content"] = f"[СЕГОДНЯ: {today}]\n{messages[0]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": f"[СЕГОДНЯ: {today}]"})

        requested_model = data.get("model", "")
        model_key = _classify(messages, requested_model)
        model_id = MODELS[model_key]["id"]
        logger.info("REQUEST: %s (%s) — %s", model_key, model_id,
                    f"stream={is_stream}" if is_stream else "sync")

        work = sanitize_payload(data)

        if is_stream:
            try:
                client, resp = await _call_nous_stream(model_id, work, timeout)
                async def stream_gen(r, c, timeout_sec):
                    try:
                        done = False
                        deadline = time.time() + max(30, timeout_sec)
                        async for chunk in r.aiter_lines():
                            if time.time() > deadline:
                                yield "data: [DONE]\n\n"
                                return
                            if chunk:
                                if not chunk.startswith("data:"):
                                    chunk = "data: " + chunk
                                yield f"{chunk}\n\n"
                        yield "data: [DONE]\n\n"
                    finally:
                        await r.aclose()
                        await c.aclose()
                return StreamingResponse(stream_gen(resp, client, timeout),
                                        media_type="text/event-stream")
            except Exception as e:
                logger.warning("STREAM FAIL: %s — fallback", e)
                async def fb_gen():
                    yield "data: " + json.dumps({
                        "choices": [{"delta": {"content": _fallback_text()},
                                     "index": 0, "finish_reason": "stop"}]
                    }) + "\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(fb_gen(), media_type="text/event-stream")

        # Последовательный каскад: small → medium → big
        cascade_order = ["small", "medium", "big"]
        start_idx = cascade_order.index(model_key)

        for attempt in cascade_order[start_idx:]:
            try:
                result = await _call_nous(MODELS[attempt]["id"], work, timeout)
                if result and result.get("choices") and result["choices"][0].get("message", {}).get("content"):
                    content = result["choices"][0]["message"]["content"]
                    logger.info("%s: ответил (%d символов)", attempt, len(content))
                    return JSONResponse(result)
            except Exception as e:
                logger.warning("%s: не ответил — %s, пробую следующую", attempt, e)

        raise Exception("Все попытки исчерпаны")

    except Exception as e:
        logger.error("CRASH: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "Hermes-4-Router", "object": "model", "owned_by": "local"},
        ]
    }

@app.get("/health")
async def health():
    return {"status": "ok", "port": 8003, "version": "1.0", "engine": "Hermes-4"}

@app.get("/status")
async def status():
    return {
        "router": "Hermes-4 Router v1.0",
        "portal_key_loaded": bool(NOUS_KEY),
        "thresholds": {
            "small_char": SMALL_CHAR_THRESHOLD,
            "big_char": BIG_CHAR_THRESHOLD,
        },
        "models": {k: v["id"] for k, v in MODELS.items()},
    }

# ============================================================================
# 7. СТАРТ
# ============================================================================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("HERMES-4 ROUTER v1.0 стартует на :8003")
    logger.info("  Portal Key: %s", "загружен" if NOUS_KEY else "НЕТ КЛЮЧА!")
    logger.info("  Small (8B):  %s  ($%.2f/M)", MODELS["small"]["id"], MODELS["small"]["cost_per_m"])
    logger.info("  Medium (70B): %s  ($%.2f/M)", MODELS["medium"]["id"], MODELS["medium"]["cost_per_m"])
    logger.info("  Big (405B):   %s  ($%.2f/M)", MODELS["big"]["id"], MODELS["big"]["cost_per_m"])
    logger.info("=" * 60)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
