#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 ZINA2 ROUTER v1.0 — DeepSeek-Only: Flash → Pro → V3
================================================================================
Порт: 8003

Три внутренних провайдера на одном DeepSeek-ключе:
  1) Flash  (deepseek-chat)     — по умолчанию, быстрый
  2) Pro    (deepseek-reasoner) — при малейшем намёке на сложность
  3) V3     (deepseek-chat)     — ручной выбор через direct DeepSeek провайдер

Чувствительность Pro: МАКСИМАЛЬНАЯ. Любая непонятка — сразу Pro.
Flash только для приветствий и односложных ответов.

Никакой лишней хуйни. Только DeepSeek.
================================================================================
"""

import sys, os, json, time, uuid, logging, asyncio, warnings, copy, random
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import httpx

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ZINA2] %(message)s")
logger = logging.getLogger("zina2_router")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Zina2 Router v1.0")

# ============================================================================
# 1. КОНФИГУРАЦИЯ
# ============================================================================
ENV_PATH = Path("/opt/zinaida/.env")

def load_env():
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
load_env()

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_KEY:
    logger.error("!!! DEEPSEEK_API_KEY не найден в .env или окружении !!!")
else:
    logger.info("DEEPSEEK_API_KEY загружен: длина=%d, начинается на %s...",
                len(DEEPSEEK_KEY), DEEPSEEK_KEY[:6])
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# Чувствительность Pro
PRO_CHAR_THRESHOLD  = int(os.getenv("ZINA2_PRO_CHAR", "150"))    # 150 символов — уже Pro
PRO_TIMEOUT         = float(os.getenv("ZINA2_TIMEOUT", "180.0"))
CONNECT_TIMEOUT     = float(os.getenv("ZINA2_CONNECT_TIMEOUT", "4.0"))

# ============================================================================
# 2. ТРИ МОДЕЛИ DeepSeek
# ============================================================================
MODELS = {
    "flash": {
        "id": "deepseek-chat",
        "name": "DeepSeek Flash (быстрый)",
    },
    "pro": {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Pro (глубокий)",
    },
    "v3": {
        "id": "deepseek-chat",  # deepseek-v3 как alias
        "name": "DeepSeek V3",
    },
}

ALLOWED_KEYS = {"model", "messages", "stream", "max_tokens", "temperature", "top_p",
                "frequency_penalty", "presence_penalty", "stop", "user", "tools",
                "tool_choice", "parallel_tool_calls", "response_format"}

# ============================================================================
# 3. ОПРЕДЕЛЕНИЕ: Flash или Pro?
#    Малейший намёк на сложность → Pro
# ============================================================================
# Слова-триггеры для Pro (любое совпадение → Pro)
PRO_TRIGGER_WORDS = {
    # Вопросы
    "что", "как", "почему", "зачем", "где", "когда", "кто", "какой", "какая",
    "какие", "какое", "сколько", "откуда", "куда", "чей",
    # Анализ
    "анализ", "анализируй", "разбери", "разбор", "объясни", "объяснение",
    "расскажи", "опиши", "покажи", "сравни", "сравнение", "найди",
    "проверь", "проверка", "исправь", "ошибка", "проблема",
    "думаю", "считаю", "полагаю", "мнение", "рассуждение",
    # Код/технологии
    "код", "скрипт", "python", "html", "css", "javascript", "js", "function",
    "api", "json", "sql", "баг", "дебаг", "debug", "ошибка",
    # Контент/креатив
    "напиши", "пост", "контент", "статья", "текст", "рассказ", "история",
    "креатив", "слоган", "заголовок", "описание",
    # Стратегия/решение
    "стратегия", "стратегический", "план", "планирование", "решение",
    "сложный", "сложно", "трудный", "трудно",
}

# Слова, при которых остаёмся на Flash (только односложное)
FLASH_ONLY_WORDS = {"привет", "пока", "да", "нет", "ок", "окей", "ладно",
                     "ага", "спасибо", "понял", "поняла", "хорошо", "норм",
                     "здравствуй", "прив"}

def _should_use_pro(messages: List[dict]) -> bool:
    """Определяет, надо ли подключать Pro.
    MAXIMUM SENSITIVITY — малейший намёк → True (Pro)."""
    if not messages:
        return False

    # Берём последнее сообщение пользователя
    last_user = None
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break

    if not last_user:
        return False

    # Если это короткое подтверждение — Flash
    text_lower = last_user.lower()

    # Только одно слово и оно из flash_only → Flash
    words = text_lower.split()
    if len(words) <= 2 and all(w.strip(".,!?") in FLASH_ONLY_WORDS for w in words):
        return False

    # Длина > PRO_CHAR_THRESHOLD → Pro
    if len(last_user) > PRO_CHAR_THRESHOLD:
        logger.info("PRO TRIGGER: длина=%d > %d", len(last_user), PRO_CHAR_THRESHOLD)
        return True

    # Есть триггер-слово → Pro
    for word in PRO_TRIGGER_WORDS:
        if word in text_lower:
            logger.info("PRO TRIGGER: слово '%s'", word)
            return True

    # Если есть символы переноса строки, форматирование → Pro
    if "\n" in last_user or "  " in last_user:
        logger.info("PRO TRIGGER: форматирование")
        return True

    # Если запрос на латинице (код/технический) → Pro
    latin_ratio = sum(1 for c in last_user if c.isascii() and c.isalpha()) / max(len(last_user), 1)
    if latin_ratio > 0.5 and len(last_user) > 10:
        logger.info("PRO TRIGGER: латиница %.0f%%", latin_ratio * 100)
        return True

    # Всё остальное → Flash
    return False

# ============================================================================
# 4. ВЫБОР МОДЕЛИ ПО ЗАПРОСУ
# ============================================================================
def _select_model(messages: List[dict], requested_model: str = "") -> str:
    """Выбирает: flash или pro. v3 — только если явно запрошен."""
    req = requested_model.lower()

    # Явный запрос V3
    if "v3" in req or "deepseek-v3" in req:
        logger.info("MODEL SELECT: V3 (явный запрос)")
        return "v3"

    # Явный запрос Pro
    if "pro" in req or "reasoner" in req:
        logger.info("MODEL SELECT: Pro (явный запрос)")
        return "pro"

    # Автовыбор
    if _should_use_pro(messages):
        logger.info("MODEL SELECT: Pro (авто — малейший намёк)")
        return "pro"

    logger.info("MODEL SELECT: Flash (по умолчанию)")
    return "flash"

# ============================================================================
# 5. ВЫЗОВ DeepSeek
# ============================================================================
async def _call_deepseek(model_id: str, payload: dict, timeout: float) -> dict:
    """Вызывает DeepSeek API с заданной моделью."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    work = copy.deepcopy(payload)
    work["model"] = model_id

    async with httpx.AsyncClient(verify=False,
            timeout=httpx.Timeout(timeout, read=timeout, connect=CONNECT_TIMEOUT)) as client:
        resp = await client.post(DEEPSEEK_URL, headers=headers, json=work)
        if resp.status_code >= 400:
            err_text = resp.text[:300]
            logger.warning("DeepSeek HTTP %d: %s", resp.status_code, err_text)
        resp.raise_for_status()
        return resp.json()

async def _call_deepseek_stream(model_id: str, payload: dict, timeout: float):
    """Стрим-вызов DeepSeek API."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    work = copy.deepcopy(payload)
    work["model"] = model_id
    work["stream"] = True

    client = httpx.AsyncClient(verify=False,
            timeout=httpx.Timeout(timeout, read=timeout, connect=CONNECT_TIMEOUT))
    try:
        resp = await client.send(
            client.build_request("POST", DEEPSEEK_URL, headers=headers, json=work),
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
# 6. ПОДГОТОВКА PAYLOAD
# ============================================================================
def sanitize_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k in ALLOWED_KEYS}


def _sanitize_sse_chunk(chunk: str) -> str:
    """Заменяет запрещённые символы (длинные тире, многоточия) в SSE-чанке DeepSeek."""
    if not chunk.startswith("data: "):
        return chunk
    try:
        data = json.loads(chunk[6:])
        for ch in data.get("choices", []):
            delta = ch.get("delta", {})
            content = delta.get("content")
            if content:
                content = content.replace("\u2014", "-").replace("\u2013", "-")
                content = content.replace("\u2026", ".")
                for bullet in ["\u2022", "\u25CF", "\u25E6"]:
                    content = content.replace(bullet, "-")
                delta["content"] = content
            msg = ch.get("message", {})
            content = msg.get("content")
            if content:
                content = content.replace("\u2014", "-").replace("\u2013", "-")
                content = content.replace("\u2026", ".")
                for bullet in ["\u2022", "\u25CF", "\u25E6"]:
                    content = content.replace(bullet, "-")
                msg["content"] = content
        return "data: " + json.dumps(data, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, IndexError):
        return chunk


def _sanitize_response_json(result: dict) -> dict:
    """Заменяет запрещённые символы в не-streaming ответе."""
    for ch in result.get("choices", []):
        msg = ch.get("message", {})
        content = msg.get("content")
        if content:
            content = content.replace("\u2014", "-").replace("\u2013", "-")
            content = content.replace("\u2026", ".")
            for bullet in ["\u2022", "\u25CF", "\u25E6"]:
                content = content.replace(bullet, "-")
            msg["content"] = content
    return result

# ============================================================================
# 7. GRACEFUL FALLBACK
# ============================================================================
def _fallback_text() -> str:
    return ("DeepSeek временно недоступен. Повтори запрос через минуту — "
            "автовосстановление уже запущено.")

def _fallback_response():
    return {
        "id": "chatcmpl-fallback", "object": "chat.completion",
        "created": int(time.time()), "model": "Zina2-Router",
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": _fallback_text()},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

# ============================================================================
# 8. HTTP-ЭНДПОИНТЫ
# ============================================================================
@app.post("/v1/chat/completions")
async def chat(request: Request):
    try:
        data = await request.json()
        is_stream = data.get("stream", False)
        timeout = float(data.get("timeout", PRO_TIMEOUT))
        messages = data.get("messages", [])
        
        # Внедряем текущую дату в system prompt
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if messages and messages[0].get("role") == "system":
            if "[СЕГОДНЯ:" not in messages[0]["content"]:
                messages[0]["content"] = f"[СЕГОДНЯ: {today}]\n{messages[0]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": f"[СЕГОДНЯ: {today}]"})
        requested_model = data.get("model", "")

        # Выбираем модель
        model_key = _select_model(messages, requested_model)
        model_id = MODELS[model_key]["id"]
        logger.info("REQUEST: %s (%s) — %s", model_key, model_id,
                    f"stream={is_stream}" if is_stream else "sync")

        # Чистим payload
        work = sanitize_payload(data)

        if is_stream:
            try:
                client, resp = await _call_deepseek_stream(model_id, work, timeout)
                logger.info("OK(stream) -> %s", model_key)

                async def stream_gen(r, c):
                    try:
                        async for chunk in r.aiter_lines():
                            if chunk:
                                chunk = _sanitize_sse_chunk(chunk)
                                yield f"{chunk}\n\n"
                    finally:
                        await r.aclose()
                        await c.aclose()

                return StreamingResponse(stream_gen(resp, client),
                                        media_type="text/event-stream")
            except Exception as e:
                logger.warning("STREAM FAIL: %s — fallback", e)
                async def fb_gen():
                    payload = {"id": "chatcmpl-fallback",
                               "object": "chat.completion.chunk",
                               "created": int(time.time()),
                               "model": "Zina2-Router",
                               "choices": [{"index": 0,
                                            "delta": {"role": "assistant",
                                                     "content": _fallback_text()},
                                            "finish_reason": None}]}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    payload["choices"][0]["delta"] = {}
                    payload["choices"][0]["finish_reason"] = "stop"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(fb_gen(), media_type="text/event-stream")

        # --- Последовательный запуск: Flash → Pro (MOA отключён 13.07.2026 по требованию Олега) ---
        try:
            # Сначала Flash (дешёвый)
            try:
                result = await _call_deepseek(MODELS["flash"]["id"], work, timeout)
                if result and result.get("choices") and result["choices"][0].get("message", {}).get("content"):
                    content = result["choices"][0]["message"]["content"]
                    logger.info("FLASH: ответил (%d символов)", len(content))
                    result = _sanitize_response_json(result)
                    return JSONResponse(result)
            except Exception as e:
                logger.warning("FLASH: не ответил — %s, пробую Pro", e)
            
            # Flash упал — Pro
            try:
                result = await _call_deepseek(MODELS["pro"]["id"], work, timeout)
                if result and result.get("choices") and result["choices"][0].get("message", {}).get("content"):
                    content = result["choices"][0]["message"]["content"]
                    logger.info("PRO: ответил (%d символов)", len(content))
                    result = _sanitize_response_json(result)
                    return JSONResponse(result)
            except Exception as e:
                logger.warning("PRO: не ответил — %s", e)
            
            raise Exception("Все попытки исчерпаны")
            
        except Exception as e:
            logger.warning("FAIL: %s — graceful fallback", e)
            return JSONResponse(_fallback_response())

    except Exception as e:
        logger.error("CRASH: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "Zina2-Router", "object": "model", "owned_by": "local"},
        ]
    }

@app.get("/health")
async def health():
    return {"status": "ok", "port": 8003, "version": "1.0"}

@app.get("/status")
async def status():
    return {
        "router": "Zina2 Router v1.0",
        "api_key_loaded": bool(DEEPSEEK_KEY),
        "pro_char_threshold": PRO_CHAR_THRESHOLD,
        "models": {k: v["id"] for k, v in MODELS.items()},
    }

# ============================================================================
# 9. СТАРТ
# ============================================================================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ZINA2 ROUTER v1.0 стартует на :8003")
    logger.info("  DeepSeek API: %s", "ключ загружен" if DEEPSEEK_KEY else "НЕТ КЛЮЧА!")
    logger.info("  Pro threshold: %d символов", PRO_CHAR_THRESHOLD)
    logger.info("  Flash: %s  |  Pro: %s  |  V3: %s",
                MODELS["flash"]["id"], MODELS["pro"]["id"], MODELS["v3"]["id"])
    logger.info("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
