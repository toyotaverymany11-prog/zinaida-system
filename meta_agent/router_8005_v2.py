#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 ZINA2 ROUTER v2.0 — DeepSeek + Бесплатные усилители
================================================================================
Порт: 8005

Архитектура:
  1. Классификатор — Ollama для приветствий, Flash для всего, Pro для сложного
  2. Server RAG — grep по файлам сервера по теме запроса
  3. Mistral-анализатор — cross-связи между файлами
  4. Генерация — DeepSeek Flash (основной) или Pro (сложный)
  5. Graceful fallback — если DeepSeek упал, отвечаем через Mistral/Ollama

Фишки:
  - 3+ ключа Mistral с ротацией при 429
  - 3+ ключа Ollama с ротацией
  - Кэширование ответов (хеш запроса -> ответ, TTL 5 мин)
  - Логирование в analytics.db
  - Чувствительность Pro — только по смыслу, не по длине
================================================================================
"""

import sys, os, json, time, uuid, logging, asyncio, warnings, copy, hashlib, sqlite3, subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import httpx

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ZINA2v2] %(message)s")
logger = logging.getLogger("zina2_router_v2")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="8005 Router v2.0")

# ============================================================================
# 1. КОНФИГУРАЦИЯ
# ============================================================================
ENV_PATH = Path("/opt/zinaida/.env")
META_ENV_PATH = Path("/opt/zinaida/meta_agent/.env")

def load_env():
    for p in [ENV_PATH, META_ENV_PATH]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())
load_env()

DEEPSEEK_KEY = ""
for p in [ENV_PATH, META_ENV_PATH]:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                    val = line.split("=", 1)[1].strip()
                    if val and val != "***" and len(val) > 10:
                        DEEPSEEK_KEY = val
                        break
        if DEEPSEEK_KEY:
            break
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

MISTRAL_KEYS = []
for env_key in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2", "MISTRAL_API_KEY_3",
                "MISTRAL_API_KEY_4", "MISTRAL_API_KEY_5"]:
    val = os.getenv(env_key, "")
    if val and val not in ("***", "") and len(val) > 10:
        MISTRAL_KEYS.append(val)
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

OLLAMA_KEYS = []
for env_key in ["OLLAMA_API_KEY", "OLLAMA_API_KEY_2", "OLLAMA_API_KEY_3",
                "GREG_OLLAMA_KEY"]:
    val = os.getenv(env_key, "")
    if val and val not in ("***", "") and len(val) > 10:
        OLLAMA_KEYS.append(val)
OLLAMA_URL = "https://ollama.com/v1/chat/completions"

# --- GitHub Models (Azure) ---
GITHUB_KEYS = []
for env_path in [Path("/opt/zinaida/config/secrets.env"), META_ENV_PATH]:
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_TOKEN") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip("'\"")
                    if val and val not in ("***", "") and len(val) > 10:
                        GITHUB_KEYS.append(val)
GITHUB_URL = "https://models.inference.ai.azure.com/chat/completions?api-version=2024-10-21"

# --- Мониторинг ---
MONITOR = {
    "total_requests": 0,
    "by_provider": {},  # mistral/github/flash/pro/ollama -> count
    "by_error": {},     # provider -> error_count
    "github_rate_limited": 0,
    "mistral_down": 0,
    "deepseek_down": 0,
    "last_alert_time": 0,
    "started_at": time.time(),
}
ALERT_COOLDOWN = 300  # 5 мин между алертами в Telegram

PRO_CHAR_THRESHOLD  = int(os.getenv("ZINA2_PRO_CHAR", "300"))
FLASH_TIMEOUT       = float(os.getenv("ZINA2_FLASH_TIMEOUT", "30.0"))
PRO_TIMEOUT         = float(os.getenv("ZINA2_PRO_TIMEOUT", "120.0"))
CONNECT_TIMEOUT     = float(os.getenv("ZINA2_CONNECT_TIMEOUT", "4.0"))
CACHE_TTL           = int(os.getenv("ZINA2_CACHE_TTL", "300"))
ANALYTICS_DB        = "/opt/zinaida/memory/analytics.db"

_mistral_key_idx = 0
_ollama_key_idx = 0
_cache = {}

# ============================================================================
# 2. МОДЕЛИ
# ============================================================================
MODELS = {
    "flash": {"id": "deepseek-chat", "name": "DeepSeek Flash", "cost_per_m": 0.27},
    "pro": {"id": "deepseek-reasoner", "name": "DeepSeek Pro", "cost_per_m": 1.42},
}

ALLOWED_KEYS = {"model", "messages", "stream", "max_tokens", "temperature", "top_p",
                "frequency_penalty", "presence_penalty", "stop", "user", "tools",
                "tool_choice", "parallel_tool_calls", "response_format"}

# ============================================================================
# 3. КЛАССИФИКАЦИЯ
# ============================================================================
PRO_TRIGGER_WORDS = {
    "анализируй", "проанализируй", "глубокий разбор", "разбери подробно",
    "сравни", "сравнение", "сопоставь", "отличие", "разница",
    "код", "скрипт", "python", "javascript", "function", "debug", "баг",
    "алгоритм", "функция", "класс", "метод", "парсер",
    "sql",
    "стратегия", "стратегический", "план действий", "roadmap",
    "архитектура", "проектирование", "спроектируй",
    "объясни подробно", "расскажи детально", "разжую", "разложи по полочкам",
}

OLLAMA_WORDS = {"привет", "пока", "да", "нет", "ок", "окей", "здравствуй"}

def _classify_request(messages: List[dict]) -> str:
    if not messages:
        return "flash"
    last_user = None
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break
    if not last_user:
        return "flash"
    text_lower = last_user.lower().strip()
    text_len = len(last_user)
    words = text_lower.split()
    if len(words) <= 2:
        clean_words = [w.strip(".,!? ") for w in words]
        if clean_words and all(w in OLLAMA_WORDS for w in clean_words):
            logger.info("CLASSIFY: ollama (приветствие)")
            return "ollama"
    if len(words) >= 3:
        for word in PRO_TRIGGER_WORDS:
            if word in text_lower:
                logger.info("CLASSIFY: pro (триггер: %s)", word)
                return "pro"
    if text_len > PRO_CHAR_THRESHOLD:
        logger.info("CLASSIFY: pro (длина %d > %d)", text_len, PRO_CHAR_THRESHOLD)
        return "pro"
    latin_ratio = sum(1 for c in last_user if c.isascii() and c.isalpha()) / max(len(last_user), 1)
    if latin_ratio > 0.4 and any(c in last_user for c in "{};:=[]"):
        logger.info("CLASSIFY: pro (код: латиница %.0f%%)", latin_ratio * 100)
        return "pro"
    logger.info("CLASSIFY: flash (по умолчанию, %d символов)", text_len)
    return "flash"

# ============================================================================
# 4. БЕСПЛАТНЫЕ УСИЛИТЕЛИ
# ============================================================================

# 4.1 Ротация ключей
def _next_mistral_key() -> Optional[str]:
    global _mistral_key_idx
    if not MISTRAL_KEYS:
        return None
    key = MISTRAL_KEYS[_mistral_key_idx % len(MISTRAL_KEYS)]
    _mistral_key_idx = (_mistral_key_idx + 1) % len(MISTRAL_KEYS)
    return key

def _next_ollama_key() -> Optional[str]:
    global _ollama_key_idx
    if not OLLAMA_KEYS:
        return None
    key = OLLAMA_KEYS[_ollama_key_idx % len(OLLAMA_KEYS)]
    _ollama_key_idx = (_ollama_key_idx + 1) % len(OLLAMA_KEYS)
    return key

# 4.2 Server RAG — поиск по файлам сервера по теме запроса
async def _search_rag(query: str) -> str:
    """Ищет файлы на сервере по теме запроса (rg через subprocess).
    Исключает: backup*, cache, sessions, node_modules, .git, __pycache__.
    Возвращает 3 куска по 500 символов.
    """
    if not query or len(query) < 10:
        return ""
    try:
        words = [w.strip(".,!?[]()\"' ") for w in query.lower().split()
                 if len(w.strip(".,!?[]()\"' ")) > 3
                 and w not in ("это", "что", "как", "для", "про", "или",
                              "блядь", "блять", "если", "когда", "там",
                              "тут", "свой", "очень", "нужно", "можно",
                              "потом", "сейчас", "будет", "такой", "какие",
                              "самый", "чтобы", "тебе", "меня", "твой",
                              "наш", "кто", "куда", "откуда", "почему",
                              "зачем", "пока", "опять", "ещё", "уже",
                              "даже", "тоже", "всё", "все", "нет",
                              "давай", "сделай", "посмотри")]
        words = words[:5]
        if not words:
            return ""

        search_pattern = "|".join(words)
        search_root = "/opt/zinaida"

        # Ищем ТОЛЬКО в ключевых папках: meta_agent, memory, shared_memory, scripts
        # rg на всю /opt/zinaida тормозит из-за backup/* (сотни МБ)
        search_dirs = [
            "/opt/zinaida/writer_rag",  # Приоритет: проверенные файлы писателя
            "/opt/zinaida/meta_agent",
            "/opt/zinaida/memory",
            "/opt/zinaida/shared_memory",
            "/opt/zinaida/scripts",
        ]

        cmd = [
            "rg", "-i", "-l", "--no-heading", "-m", "1",
            search_pattern,
            # Ищем в файлах .md .py .yaml .json .toml
            "-g", "*.md", "-g", "*.py", "-g", "*.yaml",
            "-g", "*.yml", "-g", "*.json", "-g", "*.toml",
            # Исключаем черновики, архивы, бекапы
            "--glob", "!archive/*", "--glob", "!*draft*", "--glob", "!*.bak",
        ] + search_dirs

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        paths = stdout.decode("utf-8", errors="replace").strip().split("\n")
        paths = [p for p in paths if p.strip()][:5]

        # Дополнительно ищем по имени файла — если имя содержит слово из запроса
        name_cmd = [
            "find"] + search_dirs + [
            "-maxdepth", "3", "-type", "f",
            "(", "-name", f"*{words[0]}*",
        ]
        for w in words[1:]:
            name_cmd += ["-o", "-name", f"*{w}*"]
        name_cmd += [")", "-not", "-name", "*.bak", "-not", "-name", "*.swp"]
        name_cmd += ["-not", "-path", "*backup*", "-not", "-path", "*cache*"]

        name_proc = await asyncio.create_subprocess_exec(
            *name_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            name_stdout, _ = await asyncio.wait_for(name_proc.communicate(), timeout=2.0)
            name_paths = name_stdout.decode("utf-8", errors="replace").strip().split("\n")
            name_paths = [p for p in name_paths if p.strip()]
            # Добавляем найденные по имени в начало (они релевантнее)
            if name_paths:
                paths = name_paths[:3] + paths
                logger.info("RAG: +%d файлов по имени: %s", len(name_paths), [p.split("/")[-1] for p in name_paths[:3]])
        except asyncio.TimeoutError:
            pass
        paths = paths[:5]

        if not paths:
            logger.info("RAG: ничего не найдено по '%s'", search_pattern[:60])
            return ""

        chunks = []
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = []
                    total = 0
                    for line in f:
                        lines.append(line.rstrip())
                        total += len(line)
                        if total > 500 or len(lines) >= 8:
                            break
                    chunk = "\n".join(lines)[:500]
                    if chunk:
                        rel_path = p
                        for prefix in search_dirs:
                            if p.startswith(prefix + "/"):
                                rel_path = p[len(prefix)+1:]
                                break
                        chunks.append(f"[{rel_path}]\n{chunk}")
            except Exception:
                pass

        if chunks:
            logger.info("RAG: найдено %d файлов", len(chunks))
            return "\n\n---\n\n".join(chunks)
    except asyncio.TimeoutError:
        logger.warning("RAG: timeout (3s)")
    except Exception as e:
        logger.warning("RAG fail: %s", e)
    return ""

# 4.3 Mistral-анализатор — ищет cross-связи между найденными файлами
async def _analyze_context(query: str, rag_chunks: str) -> str:
    """Mistral анализирует найденные куски: ищет связи, конфликты, релевантность."""
    if not MISTRAL_KEYS or not rag_chunks or len(rag_chunks) < 50:
        return ""
    key = _next_mistral_key()
    prompt = f"""Проанализируй найденные файлы по запросу пользователя.
Найди только РЕАЛЬНЫЕ связи (файл А ссылается на файл Б, один конфиг переопределяет другой, и т.д.).
Ничего не выдумывай. Если связей нет — ответь: Нет связей.

Запрос: {query[:300]}

Файлы:
{rag_chunks[:1500]}

Формат (только если есть связи):
🔗 Связь: [файл] -> [файл] — описание
"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(4.0, connect=3.0)) as c:
            resp = await c.post(
                MISTRAL_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "mistral-small-latest", "messages": [
                    {"role": "user", "content": prompt}
                ], "max_tokens": 300, "temperature": 0.1}
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content and "Нет связей" not in content:
                    logger.info("ANALYZE: найдены связи: %s", content[:100])
                    return content
                logger.info("ANALYZE: связей нет" if content else "ANALYZE: пустой ответ")
    except asyncio.TimeoutError:
        logger.warning("ANALYZE: timeout (4s)")
    except Exception as e:
        logger.warning("ANALYZE fail: %s", e)
    return ""

# 4.4 Fallback — если DeepSeek упал, отвечаем через Mistral/Ollama
async def _fallback_generate(messages: List[dict]) -> dict:
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break
    if MISTRAL_KEYS:
        key = _next_mistral_key()
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(30, connect=5)) as c:
                resp = await c.post(
                    MISTRAL_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "mistral-small-latest", "messages": messages,
                          "max_tokens": 1024, "temperature": 0.7}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info("FALLBACK: Mistral ответил")
                    return data
        except Exception as e:
            logger.warning("FALLBACK Mistral fail: %s", e)
    if OLLAMA_KEYS:
        key = _next_ollama_key()
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(30, connect=5)) as c:
                resp = await c.post(
                    OLLAMA_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "gemma3:4b", "messages": messages,
                          "max_tokens": 512, "temperature": 0.7}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info("FALLBACK: Ollama ответил")
                    return data
        except Exception as e:
            logger.warning("FALLBACK Ollama fail: %s", e)
    logger.error("FALLBACK: ВСЕ ПРОВАЙДЕРЫ МЁРТВЫ")
    return _build_response("Извини, сейчас проблемы с нейросетями. Попробуй через минуту.", "fallback")

# ============================================================================
# 5. ВЫЗОВ DeepSeek
# ============================================================================
async def _call_deepseek(model_id: str, payload: dict, timeout: float) -> dict:
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
# 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================
def _build_response(text: str, model_key: str, model_name: str = "") -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name or f"8005-{model_key}",
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": text},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

def sanitize_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k in ALLOWED_KEYS}

def _cache_key(messages: list) -> str:
    return hashlib.md5(json.dumps(messages, sort_keys=True).encode()).hexdigest()

def _cache_get(key: str) -> Optional[dict]:
    if key in _cache:
        resp, expiry = _cache[key]
        if time.time() < expiry:
            return resp
        del _cache[key]
    return None

def _cache_set(key: str, response: dict):
    _cache[key] = (response, time.time() + CACHE_TTL)

async def _log_request(model_used: str, char_count: int, elapsed: float, status: str):
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        conn.execute("""
            INSERT INTO requests (timestamp, model, chars, elapsed, status)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), model_used, char_count, elapsed, status))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ============================================================================
# 6.5 NEW: GitHub Models — gpt-4o бесплатно
# ============================================================================
async def _call_github(messages: List[dict], model: str = "gpt-4o", timeout: float = 30.0) -> Optional[dict]:
    """Вызов GitHub Models (gpt-4o / gpt-4o-mini) с ротацией ключей"""
    if not GITHUB_KEYS:
        return None
    for key in GITHUB_KEYS:
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(timeout, connect=5.0)) as c:
                resp = await c.post(
                    GITHUB_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "max_tokens": 3000, "temperature": 0.7}
                )
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    MONITOR["github_rate_limited"] += 1
                    logger.warning("GITHUB: rate limited (429), пробуем другой ключ")
                    continue
                else:
                    logger.warning("GITHUB: HTTP %s — %s", resp.status_code, resp.text[:100])
        except Exception as e:
            logger.warning("GITHUB call fail: %s", e)
    return None

# 6.6 NEW: Mistral с самооценкой уверенности
async def _call_mistral_with_confidence(messages: List[dict]) -> Tuple[Optional[str], float]:
    """Вызов Mistral-large + самооценка уверенности (0-100).
    Возвращает (текст_ответа, confidence). Если < 75 — ответ недостоверный."""
    if not MISTRAL_KEYS:
        return None, 0.0
    
    # Берём последний вопрос пользователя
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break
    
    # Короткие/простые — высокая уверенность по умолчанию
    if len(last_user) < 20:
        pass  # всё равно спросим
    
    prompt_messages = messages.copy()
    prompt_messages.append({
        "role": "user",
        "content": (
            f"Ответь на предыдущий вопрос. После ответа добавь строку:\n"
            f"CONFIDENCE: <число от 0 до 100>\n"
            f"Где 100 = абсолютно уверен, 0 = полностью не уверен / не знаешь.\n"
            f"Если есть хоть малейшее сомнение — ставь < 75."
        )
    })
    
    key = _next_mistral_key()
    try:
        async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(20.0, connect=5.0)) as c:
            resp = await c.post(
                MISTRAL_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "mistral-large-latest", "messages": prompt_messages,
                      "max_tokens": 2000, "temperature": 0.5}
            )
            if resp.status_code == 200:
                data = resp.json()
                full_text = data["choices"][0]["message"]["content"]
                
                # Извлекаем confidence из последней строки
                confidence = 0.0
                for line in reversed(full_text.strip().split("\n")):
                    line = line.strip()
                    if "CONFIDENCE:" in line.upper():
                        try:
                            num_str = line.split(":", 1)[1].strip().split()[0]
                            confidence = min(100.0, max(0.0, float(num_str)))
                        except:
                            confidence = 50.0
                        # Убираем строку confidence из ответа
                        full_text = full_text.replace(line, "").strip()
                        break
                
                logger.info("MISTRAL: уверенность=%.0f, длина=%d", confidence, len(full_text))
                return full_text, confidence
            elif resp.status_code == 429:
                logger.warning("MISTRAL: rate limited (429)")
            else:
                logger.warning("MISTRAL: HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("MISTRAL call fail: %s", e)
    return None, 0.0

# 6.7 NEW: Telegram алерт
async def _send_alert(message: str):
    """Отправляет сигнал в Telegram если прошло > ALERT_COOLDOWN с последнего"""
    now = time.time()
    if now - MONITOR["last_alert_time"] < ALERT_COOLDOWN:
        return  # слишком часто
    MONITOR["last_alert_time"] = now
    try:
        subprocess.run(
            ["python3", "/opt/zinaida/telegram_bot/notify.py", f"⚠️ [8005] {message}"],
            timeout=10, capture_output=True
        )
        logger.info("ALERT отправлен: %s", message)
    except Exception as e:
        logger.warning("ALERT fail: %s", e)

# 6.8 NEW: Мониторинг запросов
def _track(provider: str, ok: bool = True):
    MONITOR["total_requests"] += 1
    MONITOR["by_provider"][provider] = MONITOR["by_provider"].get(provider, 0) + 1
    if not ok:
        MONITOR["by_error"][provider] = MONITOR["by_error"].get(provider, 0) + 1

# ============================================================================
# 7. ОСНОВНОЙ ПАЙПЛАЙН
# ============================================================================
async def _generate(messages: List[dict], is_stream: bool, timeout: float,
                    requested_model: str = "") -> dict:
    start = time.time()

    # --- Шаг 1: Классификация ---
    if requested_model:
        req = requested_model.lower()
        if "pro" in req or "reasoner" in req or "enhanced" in req:
            model_key = "pro"
            if "enhanced" in req:
                logger.info("PIPELINE: VERY HIGH режим — форсирован Pro, усилители активны")
        elif "v3" in req:
            model_key = "pro"
        elif "ollama" in req:
            model_key = "ollama"
        elif "flash" in req:
            model_key = "flash"
        else:
            model_key = _classify_request(messages)
    else:
        model_key = _classify_request(messages)

    logger.info("PIPELINE: классификация = %s", model_key)

    # --- Шаг 2: Если Ollama — простой ответ через Ollama (бесплатно) ---
    if model_key == "ollama" and OLLAMA_KEYS:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()
                break
        key = _next_ollama_key()
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(10, connect=5)) as c:
                resp = await c.post(
                    OLLAMA_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "gemma3:4b", "messages": messages, "max_tokens": 50, "temperature": 0.5}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    logger.info("OLLAMA OK: ответил за %.1f сек", time.time() - start)
                    await _log_request("ollama/gemma3:4b", len(last_user), time.time() - start, "ok")
                    return _build_response(text, "ollama")
        except Exception as e:
            logger.warning("OLLAMA fail, fallback к DeepSeek Flash: %s", e)
        model_key = "flash"

    # --- Извлекаем запрос пользователя ---
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break

    # --- Шаг 3: Server RAG сначала (быстро, не параллельно — чтобы один вызов DeepSeek) ---
    rag_context = ""
    if last_user and len(last_user) > 5 and model_key != "ollama":
        rag_chunks = await _search_rag(last_user)
        if rag_chunks:
            logger.info("RAG: получено %d символов", len(rag_chunks))
            # Mistral-анализатор параллельно — не блокирует DeepSeek
            analyze_task = asyncio.create_task(_analyze_context(last_user, rag_chunks))
            rag_context = f"\n\n[КОНТЕКСТ С СЕРВЕРА]\n{rag_chunks}\n[/КОНТЕКСТ]"
        else:
            analyze_task = None
            logger.info("RAG: ничего не найдено")
    else:
        rag_chunks = ""
        analyze_task = None
        logger.info("RAG: пропущен (короткий запрос или ollama)")

    # --- Шаг 4: SUPER CASCADE — Mistral → gpt-4o → DeepSeek ---
    # Пытаемся сначала через бесплатные, DeepSeek только если не справились
    
    response_text = None
    used_provider = ""
    
    # 4a: MOA — Параллельный запуск Mistral + gpt-4o (кто быстрее и лучше)
    if model_key != "pro":  # Pro не обходим — сразу DeepSeek
        # Запускаем обе бесплатные модели параллельно
        moa_task_1 = asyncio.create_task(_call_mistral_with_confidence(messages))
        moa_task_2 = asyncio.create_task(_call_github(messages, "gpt-4o", timeout=30.0))
        
        # Ждём обе (первая вернётся быстрее)
        mistral_result = None
        github_result = None
        done, pending = await asyncio.wait(
            [moa_task_1, moa_task_2],
            timeout=25.0,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Забираем результаты (кто успел)
        for task in done:
            if task == moa_task_1:
                try:
                    mistral_text, confidence = task.result()
                    mistral_result = (mistral_text, confidence)
                    logger.info("MOA: Mistral готов, уверенность=%.0f", confidence)
                except:
                    pass
            else:
                try:
                    gh_data = task.result()
                    if gh_data:
                        gh_text = gh_data["choices"][0]["message"]["content"]
                        github_result = gh_text
                        logger.info("MOA: gpt-4o готов (%d символов)", len(gh_text))
                except:
                    pass
        
        # Отменяем то что ещё бежит (мы уже взяли результат)
        for task in pending:
            task.cancel()
        
        # Если Mistral очень уверен — берём его (бесплатно)
        if mistral_result and mistral_result[1] >= 95:
            logger.info("MOA FINAL: Mistral (уверенность %.0f) — лучший", mistral_result[1])
            response_text = mistral_result[0]
            used_provider = "mistral"
            _track("mistral", True)
        
        # Если gpt-4o ответил раньше и Mistral не уверен — берём gpt-4o
        elif github_result and (not mistral_result or mistral_result[1] < 95):
            logger.info("MOA FINAL: gpt-4o — лучший (Mistral неуверен)")
            response_text = github_result
            used_provider = "github"
            _track("github", True)
        
        # Если только Mistral и неуверен — передаём gpt-4o
        elif mistral_result and mistral_result[1] < 95:
            logger.info("MOA: Mistral (уверенность %.0f), пробуем gpt-4o как fallback", mistral_result[1])
            _track("mistral", True)  # Mistral ответил, но плохо
    
    # 4b: Если Mistral не справился — gpt-4o (GitHub, бесплатно)
    if not response_text:
        if model_key != "pro":  # Pro не обходим
            try:
                gh_messages = messages.copy()
                if rag_context:
                    for m in reversed(gh_messages):
                        if m.get("role") == "user":
                            m["content"] = f"{m['content']}\n\n---\n{rag_context}\n[/КОНТЕКСТ]"
                            break
                
                gh_data = await _call_github(gh_messages, "gpt-4o", timeout=30.0)
                if gh_data:
                    gh_text = gh_data["choices"][0]["message"]["content"]
                    logger.info("GITHUB CASCADE: gpt-4o ответил (%d символов)", len(gh_text))
                    response_text = gh_text
                    used_provider = "github"
                    _track("github", True)
                else:
                    logger.warning("GITHUB CASCADE: не ответил, пробуем DeepSeek")
                    _track("github", False)
            except Exception as e:
                logger.warning("GITHUB CASCADE error: %s", e)
                _track("github", False)
    
    # 4c: DeepSeek Flash (если бесплатные не справились или модель Pro)
    if not response_text:
        model_key_ds = model_key
        model_id = MODELS.get(model_key_ds, MODELS["flash"])["id"]
        ds_payload = sanitize_payload({"messages": messages, "max_tokens": 4096, "temperature": 0.7})
        
        if rag_context:
            enriched = copy.deepcopy(ds_payload)
            for m in reversed(enriched["messages"]):
                if m.get("role") == "user":
                    m["content"] = f"{m['content']}\n\n---\nВот информация с сервера по теме:\n{rag_context}\n\nИспользуй её в ответе — ответь точнее и полезнее. Не упоминай что получил контекст."
                break
            ds_payload = enriched
            logger.info("DEEPSEEK: контекст добавлен (%d символов), один вызов", len(rag_context))

        try:
            ds_timeout = PRO_TIMEOUT if model_key == "pro" else FLASH_TIMEOUT
            logger.info("CALL DS: model=%s, timeout=%s", model_id, ds_timeout)
            result = await _call_deepseek(model_id, ds_payload, ds_timeout)
            response_text = result["choices"][0]["message"]["content"]
            logger.info("DEEPSEEK (%s) OK: %d символов за %.1f сек",
                        model_key, len(response_text), time.time() - start)

            if rag_context and analyze_task:
                try:
                    analyze_result = await asyncio.wait_for(analyze_task, timeout=3.0)
                    if analyze_result:
                        logger.info("ANALYZE: %s", analyze_result[:100])
                except asyncio.TimeoutError:
                    logger.warning("ANALYZE: timeout")

            for male, female in [
                (" понял ", " поняла "), (" сделал ", " сделала "), (" пошел ", " пошла "),
                (" пошёл ", " пошла "), (" написал ", " написала "), (" сказал ", " сказала "),
                (" проверил ", " проверила "), (" запустил ", " запустила "),
                (" поправил ", " поправила "), (" начал ", " начала "),
                (" думал ", " думала "), (" ответил ", " ответила "),
                (" решил ", " решила "), (" зашел ", " зашла "), (" зашёл ", " зашла "),
                (" вышел ", " вышла "), (" пришел ", " пришла "), (" пришёл ", " пришла "),
                (" ушел ", " ушла "), (" ушёл ", " ушла "), (" увидел ", " увидела "),
                (" услышал ", " услышала "), (" открыл ", " открыла "),
                (" закрыл ", " закрыла "), (" взял ", " взяла "),
                (" дал ", " дала "), (" нашёл ", " нашла "), (" нашел ", " нашла "),
                (" встал ", " встала "), (" сел ", " села "),
                (" лег ", " легла "), (" лёг ", " легла "),
            ]:
                if male in response_text.lower():
                    idx = response_text.lower().find(male)
                    if idx >= 0:
                        before = response_text[:idx]
                        after = response_text[idx+len(male):]
                        response_text = before + female + after

            elapsed = time.time() - start
            await _log_request(f"deepseek/{model_key}", len(last_user), elapsed, "ok")
            _track(model_key, True)
            return _build_response(response_text, model_key, f"8005-{model_key}")

        except Exception as e:
            logger.warning("DEEPSEEK %s fail: %s — fallback к бесплатным", model_key, e)
            _track(model_key, False)
            MONITOR["deepseek_down"] += 1
            elapsed = time.time() - start
            await _log_request(f"deepseek/{model_key}", len(last_user), elapsed, f"fail:{str(e)[:50]}")
            # Если DeepSeek падает >3 раз подряд — сигнал в Telegram
            if MONITOR["deepseek_down"] > 3:
                await _send_alert(f"DeepSeek упал {MONITOR['deepseek_down']} раз: {str(e)[:80]}")
            fallback_result = await _fallback_generate(messages)
            return fallback_result

    # 4d: Cascade result (Mistral или gpt-4o ответили без DeepSeek)
    if response_text and used_provider in ("mistral", "github"):
        _male_to_female = [
            (" понял ", " поняла "), (" сделал ", " сделала "), (" пошел ", " пошла "),
            (" пошёл ", " пошла "), (" написал ", " написала "), (" сказал ", " сказала "),
            (" проверил ", " проверила "), (" запустил ", " запустила "),
            (" поправил ", " поправила "), (" начал ", " начала "),
            (" думал ", " думала "), (" ответил ", " ответила "),
            (" решил ", " решила "), (" зашел ", " зашла "), (" зашёл ", " зашла "),
            (" вышел ", " вышла "), (" пришел ", " пришла "), (" пришёл ", " пришла "),
            (" ушел ", " ушла "), (" ушёл ", " ушла "), (" увидел ", " увидела "),
            (" услышал ", " услышала "), (" открыл ", " открыла "),
            (" закрыл ", " закрыла "), (" взял ", " взяла "),
            (" дал ", " дала "), (" нашёл ", " нашла "), (" нашел ", " нашла "),
            (" встал ", " встала "), (" сел ", " села "),
            (" лег ", " легла "), (" лёг ", " легла "),
        ]
        for male, female in _male_to_female:
            if male in response_text.lower():
                idx = response_text.lower().find(male)
                if idx >= 0:
                    before = response_text[:idx]
                    after = response_text[idx+len(male):]
                    response_text = before + female + after
        
        elapsed = time.time() - start
        await _log_request(used_provider, len(last_user), elapsed, "ok")
        logger.info("CASCADE: ответ через %s (%d символов, %.1fс)", used_provider, len(response_text), elapsed)
        return _build_response(response_text, used_provider, f"8005-{used_provider}")


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
        requested_model = data.get("model", "")

        cache_key = _cache_key(messages)
        cached = _cache_get(cache_key)
        if cached:
            logger.info("CACHE HIT: возвращаю кэшированный ответ")
            cached["created"] = int(time.time())
            return JSONResponse(cached)

        if is_stream:
            model_key = _classify_request(messages) if not requested_model else "flash"
            if "pro" in requested_model.lower() or "reasoner" in requested_model.lower():
                model_key = "pro"
            model_id = MODELS.get(model_key, MODELS["flash"])["id"]
            payload = sanitize_payload(data)
            try:
                client, resp = await _call_deepseek_stream(model_id, payload, timeout)
                async def stream_gen(r, c):
                    try:
                        async for chunk in r.aiter_lines():
                            if chunk:
                                yield f"{chunk}\n\n"
                    finally:
                        await r.aclose()
                        await c.aclose()
                return StreamingResponse(stream_gen(resp, client), media_type="text/event-stream")
            except Exception as e:
                logger.warning("STREAM FAIL: %s — fallback", e)
                async def fb_gen():
                    fb = _build_response("Сервис временно недоступен. Попробуй через минуту.", "fallback")
                    payload_chunk = {
                        "id": fb["id"], "object": "chat.completion.chunk",
                        "created": fb["created"], "model": "8005-Fallback",
                        "choices": [{"index": 0, "delta": {"role": "assistant",
                                                           "content": "Сервис временно недоступен. Попробуй через минуту."},
                                     "finish_reason": None}]}
                    yield f"data: {json.dumps(payload_chunk, ensure_ascii=False)}\n\n"
                    payload_chunk["choices"][0]["delta"] = {}
                    payload_chunk["choices"][0]["finish_reason"] = "stop"
                    yield f"data: {json.dumps(payload_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(fb_gen(), media_type="text/event-stream")

        result = await _generate(messages, False, timeout, requested_model)
        _cache_set(cache_key, result)
        return JSONResponse(result)

    except Exception as e:
        logger.error("CRASH: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "8005-Router", "object": "model", "owned_by": "local"},
            {"id": "8005-Enhanced", "object": "model", "owned_by": "local"},
            {"id": "8005-Flash", "object": "model", "owned_by": "local"},
            {"id": "8005-Pro", "object": "model", "owned_by": "local"},
        ]
    }

@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Возвращаем информацию о конкретной модели, чтобы Hermes не падал с 404."""
    known = {"8005-Router", "8005-Enhanced", "8005-Flash", "8005-Pro"}
    if model_id in known:
        return {"id": model_id, "object": "model", "owned_by": "local"}
    return JSONResponse({"error": f"Model '{model_id}' not found"}, status_code=404)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "port": 8005,
        "version": "2.0",
        "deepseek": bool(DEEPSEEK_KEY),
        "deepseek_key_preview": DEEPSEEK_KEY[:10] + "..." if DEEPSEEK_KEY else "none",
        "mistral_keys": len(MISTRAL_KEYS),
        "ollama_keys": len(OLLAMA_KEYS),
    }

@app.get("/status")
async def status():
    runtime = time.time() - MONITOR["started_at"]
    monitor = dict(MONITOR)
    monitor.pop("started_at", None)
    monitor.pop("last_alert_time", None)
    monitor["runtime_hours"] = round(runtime / 3600, 1)
    
    # Статус ключей
    gh1_ok = bool(GITHUB_KEYS) and len(GITHUB_KEYS) >= 1
    gh2_ok = bool(GITHUB_KEYS) and len(GITHUB_KEYS) >= 2
    ds_ok = bool(DEEPSEEK_KEY)
    mistral_ok = len(MISTRAL_KEYS) >= 1
    
    # Предупреждения
    warnings_list = []
    if MONITOR["github_rate_limited"] > 5:
        warnings_list.append(f"github_rate_limited={MONITOR['github_rate_limited']}")
    if MONITOR["deepseek_down"] > 3:
        warnings_list.append(f"deepseek_down={MONITOR['deepseek_down']}")
    
    return {
        "router": "8005 Router v2.0 — Super Cascade",
        "deepseek_key_loaded": ds_ok,
        "mistral_keys_loaded": len(MISTRAL_KEYS),
        "ollama_keys_loaded": len(OLLAMA_KEYS),
        "github_keys_loaded": len(GITHUB_KEYS),
        "github_keys_ok": f"{'✅' if gh1_ok else '❌'} основной, {'✅' if gh2_ok else '❌'} запасной",
        "pro_char_threshold": PRO_CHAR_THRESHOLD,
        "cache_entries": len(_cache),
        "models": {k: v["id"] for k, v in MODELS.items()},
        "cascade": {
            "1_ollama": "приветствия (бесплатно)",
            "2_mistral": "обычные запросы с самооценкой (бесплатно)",
            "3_github_gpt4o": "сложные через gpt-4o (бесплатно)",
            "4_deepseek_flash": "если бесплатные не справились ($0.27/M)",
            "5_deepseek_pro": "экстрим ($1.42/M)",
        },
        "amplifiers": {
            "server_rag": "rg поиск по файлам сервера по теме (бесплатно)",
            "analyze": "Mistral ищет cross-связи между файлами (бесплатно)",
            "fallback": "Mistral -> Ollama если DeepSeek упал",
        },
        "monitor": monitor,
        "warnings": warnings_list if warnings_list else "нет",
        "github_ok": "✅" if gh1_ok else "❌",
    }

# ============================================================================
# 9. СТАРТ
# ============================================================================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ZINA2 ROUTER v2.0 стартует на :8005")
    logger.info("  DeepSeek:   %s", "ключ загружен" if DEEPSEEK_KEY else "НЕТ КЛЮЧА!")
    logger.info("  Mistral:    %d ключей", len(MISTRAL_KEYS))
    logger.info("  Ollama:     %d ключей", len(OLLAMA_KEYS))
    logger.info("  Server RAG: вкл (rg по /opt/zinaida/)")
    logger.info("  Анализатор: вкл (Mistral cross-связи)")
    logger.info("  Pro порог:  %d символов", PRO_CHAR_THRESHOLD)
    logger.info("  Кэш TTL:    %d сек", CACHE_TTL)
    logger.info("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="info", log_config=None)
