#!/usr/bin/env python3
"""
deep_research.py — многоагентная система глубокого исследования.
4 раунда: Сбор → Вопросы → Добивка → Синтез.

Роли агентов (Раунд 1):
  - Mistral → Tavily, широкий обзор темы
  - Mistral2 → DuckDuckGo, второй поисковик (другие результаты)
  - GitHub → ПОИСК ПО СЕРВЕРУ (/opt/zinaida/, файлы, базы)
  - Ollama → Tavily, узкий запрос (цифры, даты, конкретика)

Синтез: DeepSeek V3 (только Раунд 4 + Раунд 2 оценка)
"""

import os
import sys
import json
import time
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Optional

import requests

# ─── КОНСТАНТЫ ───────────────────────────────────────────────────────────────

AGENTS = [
    ("mistral",     "Mistral — широкий обзор (BrightData)",      "tavily_broad"),
    ("mistral2",    "Mistral — DuckDuckGo (другой поисковик)",     "duckduckgo"),
    ("github",      "GitHub — поиск по серверу (/opt/zinaida/)",  "server_search"),
    ("ollama",      "Ollama — узкий запрос (BrightData, цифры/даты/конкретика)", "tavily_narrow"),
]

AGENT_TIMEOUT = 120
TAVILY_MAX_RESULTS = 5
DDG_MAX_RESULTS = 5  # DuckDuckGo результатов
SERVER_SEARCH_DEPTH = 50  # макс результатов поиска по серверу

# URL моделей
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
OLLAMA_API_URL = "https://ollama.com/v1/chat/completions"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
TAVILY_API_URL = "https://api.tavily.com/search"

OUTPUT_BASE = Path("/opt/zinaida/sandbox/deep_research")

# ─── ЛОГГЕР ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S", stream=sys.stdout)
log = logging.getLogger("deep_research")

def agent_log(agent_name: str, msg: str):
    log.info("[%s] %s", agent_name, msg)

# ─── ЗАГРУЗКА КЛЮЧЕЙ ────────────────────────────────────────────────────────

def _parse_dotenv(path: str) -> dict:
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip().strip("'\"")
    except FileNotFoundError:
        pass
    return result

def load_config() -> dict:
    cfg = {}
    main_env = _parse_dotenv("/opt/zinaida/.env")
    cfg["DEEPSEEK_API_KEY"] = main_env.get("DEEPSEEK_API_KEY", "")
    secrets_env = _parse_dotenv("/opt/zinaida/config/secrets.env")
    cfg["MISTRAL_API_KEY"] = secrets_env.get("MISTRAL_API_KEY", "")
    cfg["MISTRAL_API_KEY_2"] = secrets_env.get("MISTRAL_API_KEY_2", "")
    cfg["MISTRAL_API_KEY_3"] = secrets_env.get("MISTRAL_API_KEY_3", "")
    cfg["OLLAMA_API_KEY_1"] = secrets_env.get("OLLAMA_API_KEY_1", "")
    cfg["OLLAMA_API_KEY_2"] = secrets_env.get("OLLAMA_API_KEY_2", "")
    cfg["OLLAMA_API_KEY_3"] = secrets_env.get("OLLAMA_API_KEY_3", "")
    cfg["GITHUB_TOKEN"] = secrets_env.get("GITHUB_TOKEN", "")
    hermes_env = _parse_dotenv("/root/.hermes/.env")
    cfg["TAVILY_API_KEY"] = hermes_env.get("TAVILY_API_KEY", "")
    if not cfg.get("GITHUB_TOKEN"):
        cfg["GITHUB_TOKEN"] = hermes_env.get("GITHUB_TOKEN", "")
    return cfg

# ─── ПОИСК ───────────────────────────────────────────────────────────────────

def brightdata_search(query: str, max_results: int = 5) -> list:
    """Поиск через BrightData SERP API."""
    try:
        import subprocess, json
        r = subprocess.run(
            ["python3", "/opt/zinaida/scripts/web_search_brightdata.py", query, "--limit", str(max_results)],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(r.stdout)
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "raw_content": item.get("snippet", ""),
                "source": "brightdata",
            })
        if results:
            agent_log("brightdata", f"✅ Найдено {len(results)} результатов")
        return results
    except Exception as e:
        agent_log("brightdata", f"❌ Ошибка: {e}")
        return []


def cascade_search(query: str, max_results: int = 5) -> list:
    """Каскадный поиск: BrightData → DuckDuckGo → Server."""
    # 1. BrightData
    results = brightdata_search(query, max_results)
    if results:
        return results
    agent_log("cascade", "BrightData не сработал → DuckDuckGo")

    # 2. DuckDuckGo
    results = ddgs_search(query, max_results)
    if results:
        return results
    agent_log("cascade", "DuckDuckGo не сработал → поиск по серверу")

    # 3. Поиск по серверу
    server_text = server_search(query)
    if server_text:
        return [{"title": "Результаты поиска по серверу", "url": "", "content": server_text[:500], "raw_content": server_text[:500], "source": "server"}]

    agent_log("cascade", "❌ Все источники поиска недоступны")
    return []


def tavily_search(key: str, query: str, max_results: int = TAVILY_MAX_RESULTS) -> list:
    """Запасной поиск через BrightData."""
    return cascade_search(query, max_results)

def ddgs_search(query: str, max_results: int = DDG_MAX_RESULTS) -> list:
    """Поиск через DuckDuckGo — бесплатно, без API ключа."""
    try:
        from ddgs import DDGS
        s = DDGS()
        raw = s.text(query, max_results=max_results)
        results = []
        for item in raw:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "content": item.get("body", ""),
                "raw_content": item.get("body", ""),
                "source": "duckduckgo",
            })
        return results
    except Exception as e:
        agent_log("ddgs", f"Ошибка: {e}")
        return []

def server_search(query: str) -> str:
    """Поиск по локальным файлам сервера. Ищет в /opt/zinaida/."""
    agent_log("server_search", f"Ищу по серверу: {query}")
    results = []
    # Извлекаем ключевые слова из запроса (первые 2-3 слова)
    keywords = [w for w in query.lower().split() if len(w) > 3][:3]
    if not keywords:
        keywords = [query[:20]]

    for kw in keywords:
        try:
            cmd = f"grep -r -l -i --include='*.md' --include='*.txt' --include='*.py' --include='*.json' --include='*.db' '{kw}' /opt/zinaida/ 2>/dev/null | head -10"
            out = subprocess.check_output(cmd, shell=True, timeout=10).decode("utf-8", errors="replace").strip()
            if out:
                for filepath in out.split("\n")[:10]:
                    try:
                        size = os.path.getsize(filepath)
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            snippet = f.read(2000)
                        # Выделяем релевантную часть
                        idx = snippet.lower().find(kw)
                        if idx > 0:
                            start = max(0, idx - 200)
                            end = min(len(snippet), idx + 400)
                            snippet = snippet[start:end]
                        results.append({
                            "title": f"Файл: {filepath}",
                            "url": filepath,
                            "content": snippet,
                            "raw_content": snippet,
                            "source": "server",
                            "size": size,
                        })
                    except:
                        pass
        except:
            pass

    # Также ищем в базах данных SQLite
    try:
        import sqlite3
        db_paths = [
            "/opt/zinaida/inbox/PROJECTS/Otnoshenya/phases.db",
            "/opt/zinaida/memory/smm_rag.db",
        ]
        for db_path in db_paths:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Ищем по всем текстовым полям
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    for (table_name,) in tables[:5]:
                        try:
                            cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
                            create_sql = cursor.fetchone()
                            if create_sql and "text" in create_sql[0].lower():
                                for kw in keywords:
                                    cursor.execute(f"SELECT * FROM \"{table_name}\" WHERE * LIKE '%{kw}%' LIMIT 3")
                                    rows = cursor.fetchall()
                                    if rows:
                                        results.append({
                                            "title": f"База: {db_path} → {table_name}",
                                            "url": f"sqlite://{db_path}/{table_name}",
                                            "content": str(rows[0])[:2000],
                                            "raw_content": str(rows[0])[:2000],
                                            "source": "server_db",
                                        })
                        except:
                            pass
                except:
                    pass
                conn.close()
    except:
        pass

    return results[:SERVER_SEARCH_DEPTH]

def web_extract(url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        text = resp.text
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000] + ("..." if len(text) > 8000 else "")
    except Exception as e:
        agent_log("web_extract", f"Ошибка {url}: {e}")
        return None

# ─── API ВЫЗОВЫ LLM ──────────────────────────────────────────────────────────

def call_llm(url, model, api_key, messages, temperature=0.3, max_tokens=4096, timeout=60, extra_headers=None):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"].get("content")
        return None
    except Exception as e:
        log.warning("LLM error (%s): %s", model, e)
        return None

def call_mistral(api_key, messages, timeout=60):
    return call_llm(MISTRAL_API_URL, "mistral-small-latest", api_key, messages, timeout=timeout)

def call_github(api_key, messages, timeout=60):
    return call_llm(GITHUB_MODELS_URL, "gpt-4o-mini", api_key, messages, timeout=timeout)

def call_ollama(api_key, messages, timeout=60):
    return call_llm(OLLAMA_API_URL, "gemma3:4b", api_key, messages, timeout=timeout)

def call_deepseek(api_key, messages, timeout=180):
    return call_llm(DEEPSEEK_API_URL, "deepseek-chat", api_key, messages, temperature=0.2, max_tokens=8192, timeout=timeout)

# ─── ПРОМПТЫ ─────────────────────────────────────────────────────────────────

PROMPT_ROUND1_SUMMARIZE = """Ты — исследовательский агент с ролью: {role}. Твоя задача — по теме "{topic}" найти информацию и составить конспект.

Результаты поиска/данные:

{search_results}

Напиши конспект 5-10 bullet points. Для каждого: факт, цитата (если есть), ссылка на источник.
Формат: • [факт] — источник: [цитата] — {{url}}
"""

PROMPT_ROUND2_QUESTIONS = """Ты — аналитик. Прочитай конспекты от 4 агентов по теме "{topic}".

{agent_summaries}

Сформулируй 3 вопроса по существу. Каждый вопрос ДОЛЖЕН ссылаться на конкретный факт из конспекта и требовать углублённого поиска.

Формат:
Q1: [вопрос] — на основе конспекта [агент]: [факт]
Q2: [вопрос] — на основе конспекта [агент]: [факт]
Q3: [вопрос] — на основе конспекта [агент]: [факт]
"""

PROMPT_ROUND3_FOLLOWUP = """По теме "{topic}" задан вопрос: {question}
Результаты поиска: {search_results}
Напиши краткий ответ (2-4 предложения) с цитатами и ссылками."""

PROMPT_ROUND4_SYNTHESIS = '''Ты — DeepSeek Pro, главный аналитик и ВЕРИФИКАТОР. Синтезируй итоговый отчёт по теме "{topic}".

## ЖЁСТКОЕ ПРАВИЛО ФАКТ-ЧЕКА
Ты НЕ просто пишешь отчёт. Ты проверяешь каждый факт:

1. **✅ ПОДТВЕРЖДЁННЫЙ ФАКТ** — указан минимум в 2 независимых источниках или есть прямая ссылка
2. **⚠️ ТРЕБУЕТ ПРОВЕРКИ** — факт указан в 1 источнике, нет подтверждения от других агентов
3. **❌ ГАЛЛЮЦИНАЦИЯ/ВЫДУМКА** — нет источников, противоречит другим агентам, звучит неправдоподобно

В раздел "Факты и цифры" попадают ТОЛЬКО подтверждённые факты (✅).
Всё, что ❌ — в отдельный блок "Отсеяно".
Всё, что ⚠️ — в "Требует проверки".

## Конспекты агентов
{agent_summaries}

## Вопросы и ответы
{qa_section}

## Не ответившие агенты
{dead_agents}

Составь структурированный отчёт:
# Глубокое исследование: [тема]
Дата: {date}
Источники: [N]

## 1. Ключевые выводы
Только проверенные. Без воды.

## 2. Факты и цифры
- [факт] — ✅ [ссылка]
- [факт] — ✅ [ссылка]

## 3. Отсеяно (❌ галлюцинации/выдумки)
- [пункт] — почему отсеяно

## 4. Требует проверки (⚠️)
- [пункт] — что проверить

## 5. Анализ противоречий
...

## 6. Итоговый вердикт
...'''

# ─── РАУНД 1: СБОР ──────────────────────────────────────────────────────────

def generate_search_query(topic: str, role: str, agent_name: str) -> tuple:
    """
    Генерирует поисковый запрос в зависимости от роли агента.
    Возвращает (текст_запроса, роль_для_промпта)
    """
    role_descriptions = {
        "tavily_broad": ("широкий обзор темы, главные факты, общая картина",
                         f"Широкий обзор. Запрос: {topic}"),
        "duckduckgo": ("поиск через DuckDuckGo, найти информацию с другого ракурса",
                       f"Поиск другим поисковиком. Запрос: {topic}"),
        "server_search": ("поиск по локальным файлам сервера, базам знаний, проектам",
                          f"Поиск по своим данным. Запрос: {topic}"),
        "tavily_narrow": ("конкретные цифры, даты, имена, статистика, точные данные",
                          f"Узкий поиск конкретики. Запрос: {topic}. Год 2025-2026"),
    }
    return role_descriptions.get(role, ("общий поиск", topic))

def run_agent_round1(agent_name: str, agent_label: str, role: str, topic: str, cfg: dict) -> Optional[dict]:
    agent_log(agent_name, f"Роль: {role}. Тема: {topic[:60]}...")
    search_query, role_text = generate_search_query(topic, role, agent_name)
    results = []
    search_summary = ""

    if role == "server_search":
        # GitHub — поиск по серверу
        server_data = server_search(topic)
        if server_data:
            agent_log(agent_name, f"На сервере найдено {len(server_data)} результатов")
            for i, item in enumerate(server_data[:10], 1):
                title = item.get("title", "")
                content = item.get("content", "")[:1000]
                url = item.get("url", "")
                search_summary += f"\n--- Результат {i}: {title} ---\nURL: {url}\n{content}\n"
        if not search_summary:
            search_summary = "(ничего не найдено на сервере)"

    elif role == "duckduckgo":
        # Mistral2 — DuckDuckGo
        results = ddgs_search(topic)
        agent_log(agent_name, f"DuckDuckGo вернул {len(results)} результатов")
        for i, item in enumerate(results[:5], 1):
            content = item.get("raw_content", "") or item.get("content", "")
            if len(content) > 2000:
                content = content[:2000]
            search_summary += f"\n--- Результат {i}: {item.get('title', '')} [DuckDuckGo] ---\nURL: {item.get('url', '')}\n{content}\n"
        if not search_summary:
            search_summary = "(DuckDuckGo ничего не вернул)"

    else:
        # Каскад: BrightData → DuckDuckGo → Server (через tavily_search)
        if role == "tavily_narrow":
            tavily_query = f"{topic} цифры статистика данные 2025 2026"
        else:
            tavily_query = topic

        results = tavily_search("", tavily_query)
        source = results[0].get("source", "?") if results else "none"
        agent_log(agent_name, f"Поиск ({source}) вернул {len(results)} результатов")
        for i, item in enumerate(results[:5], 1):
            raw = item.get("raw_content", "") or item.get("content", "")
            if len(raw) > 2000:
                raw = raw[:2000]
            search_summary += f"\n--- Результат {i}: {item.get('title', '')} [{item.get('source','?')}] ---\nURL: {item.get('url', '')}\n{raw}\n"
        if not search_summary:
            search_summary = "(поиск ничего не вернул)"

    # LLM генерация конспекта
    prompt = PROMPT_ROUND1_SUMMARIZE.format(topic=topic, role=role_text, search_results=search_summary)
    messages = [{"role": "user", "content": prompt}]
    agent_log(agent_name, "Генерирую конспект...")

    result = None
    if agent_name in ("mistral", "mistral2"):
        for key_name in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2", "MISTRAL_API_KEY_3"]:
            key = cfg.get(key_name, "")
            if key:
                result = call_mistral(key, messages)
                if result:
                    break
    elif agent_name == "github":
        result = call_github(cfg.get("GITHUB_TOKEN", ""), messages)
        if not result:
            agent_log(agent_name, "GitHub упал, пробую Mistral как fallback...")
            for key_name in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2"]:
                key = cfg.get(key_name, "")
                if key:
                    result = call_mistral(key, messages)
                    if result:
                        agent_log(agent_name, "Fallback на Mistral сработал")
                        break
    elif agent_name == "ollama":
        for key_name in ["OLLAMA_API_KEY_1", "OLLAMA_API_KEY_2", "OLLAMA_API_KEY_3"]:
            key = cfg.get(key_name, "")
            if key:
                result = call_ollama(key, messages)
                if result:
                    break
    if not result:
        agent_log(agent_name, "Не удалось получить ответ")
        return None
    agent_log(agent_name, f"Конспект готов ({len(result)} символов)")
    return {"agent": agent_name, "label": agent_label, "role": role, "summary": result, "search_data": search_summary}

def round1_parallel(topic: str, cfg: dict) -> dict:
    log.info("=== РАУНД 1: СБОР (роли разделены) ===")
    names = [a[0] for a in AGENTS]
    results = {}
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
        future_map = {executor.submit(run_agent_round1, a[0], a[1], a[2], topic, cfg): a[0] for a in AGENTS}
        for future in as_completed(future_map, timeout=AGENT_TIMEOUT + 10):
            agent = future_map[future]
            try:
                res = future.result(timeout=5)
                if res:
                    results[agent] = res
                else:
                    results[agent] = None
                    agent_log(agent, "Вернул null")
            except TimeoutError:
                results[agent] = None
                agent_log(agent, "TIMEOUT")
            except Exception as e:
                results[agent] = None
                agent_log(agent, f"Ошибка: {e}")
    for a in names:
        if a not in results:
            results[a] = None
    ok = sum(1 for v in results.values() if v)
    log.info(f"Раунд 1: {ok}/{len(AGENTS)} агентов ответили")
    return results

# ─── РАУНД 2: ВОПРОСЫ ──────────────────────────────────────────────────────

def round2_questions(topic: str, summaries: dict, cfg: dict) -> dict:
    log.info("=== РАУНД 2: ВОПРОСЫ ===")
    names = [a[0] for a in AGENTS]
    questions = {}
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
        future_map = {}
        for a_name, a_label, _ in AGENTS:
            prompt = PROMPT_ROUND2_QUESTIONS.format(topic=topic, agent_summaries=_build_summary_block(summaries))
            messages = [{"role": "user", "content": prompt}]
            future = executor.submit(_call_agent_llm, a_name, messages, cfg)
            future_map[future] = a_name
        for future in as_completed(future_map, timeout=AGENT_TIMEOUT + 10):
            agent = future_map[future]
            try:
                result = future.result(timeout=10)
                questions[agent] = result
            except:
                questions[agent] = None
    for a in names:
        if a not in questions:
            questions[a] = None

    # DeepSeek оценивает вопросы
    log.info("DeepSeek Pro оценивает вопросы...")
    all_q = "\n".join([f"\n=== {a} ===\n{q or '(не ответил)'}" for a, q in questions.items()])
    eval_prompt = f"""Оцени вопросы по теме "{topic}":
{all_q}
✅ ГОДНЫЙ: содержит конкретный факт/цифру, требует углублённого поиска
❌ МУСОР: общий вопрос без конкретики
Формат: Q (агент): ✅/❌ — поисковый запрос: [формулировка]"""
    evaluation = call_deepseek(cfg["DEEPSEEK_API_KEY"], [{"role": "user", "content": eval_prompt}])
    return {"questions": questions, "evaluation": evaluation or ""}

def _build_summary_block(summaries: dict) -> str:
    parts = []
    for a_name, a_label, _ in AGENTS:
        if summaries.get(a_name):
            parts.append(f"### {a_label}\n{summaries[a_name]['summary']}\n")
        else:
            parts.append(f"### {a_label}\n(не ответил)\n")
    return "\n".join(parts)

def _call_agent_llm(agent_name: str, messages: list, cfg: dict) -> Optional[str]:
    if agent_name in ("mistral", "mistral2"):
        for k in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2", "MISTRAL_API_KEY_3"]:
            key = cfg.get(k, "")
            if key:
                r = call_mistral(key, messages)
                if r:
                    return r
    elif agent_name == "github":
        r = call_github(cfg.get("GITHUB_TOKEN", ""), messages)
        if r:
            return r
        for k in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2"]:
            key = cfg.get(k, "")
            if key:
                r = call_mistral(key, messages)
                if r:
                    return r
    elif agent_name == "ollama":
        for k in ["OLLAMA_API_KEY_1", "OLLAMA_API_KEY_2", "OLLAMA_API_KEY_3"]:
            key = cfg.get(k, "")
            if key:
                r = call_ollama(key, messages)
                if r:
                    return r
    return None

def parse_approved_questions(evaluation: str, questions: dict) -> list:
    """Парсит годные вопросы из оценки DeepSeek.
    Формат оценки: **Q1:** ✅ **ГОДНЫЙ** или | agent | Q3 | ✅ ГОДНЫЙ |
    Если нет явного поискового запроса — используем сам вопрос как запрос.
    """
    approved = []

    # Собираем все вопросы от агентов
    all_questions = {}
    for agent, q_data in questions.items():
        # q_data может быть строкой (сами вопросы) или словарём {"agent":..., "questions":...}
        if isinstance(q_data, dict):
            q_text = q_data.get("questions", "")
        elif isinstance(q_data, str):
            q_text = q_data
        else:
            continue
        if q_text:
            for line in q_text.strip().split("\n"):
                line = line.strip()
                if line.startswith("Q") and ":" in line:
                    clean_line = re.sub(r"\*\*", "", line)
                    parts = clean_line.split(":", 1)
                    if len(parts) > 1:
                        qid = parts[0].strip()
                        qcontent = parts[1].strip()
                        all_questions[qid] = qcontent

    # Парсим оценку: ищем строки вида "Q1: ✅" или "Q1 | ✅" или "Q1: ❌"
    for line in evaluation.split("\n"):
        line = line.strip()
        # Ищем паттерн: Q1, Q2 или Q3 с ✅ после
        m = re.search(r"Q(\d+)\s*[:|]\s*(.*?)(✅|❌)", line)
        if m:
            qid = f"Q{m.group(1)}"
            is_good = "✅" in m.group(3)
            if is_good and qid in all_questions:
                approved.append(all_questions[qid][:150])

    # Fallback: если ничего не нашли, берём все Q с ✅ из строк
    if not approved:
        lines_by_q = {}
        current_q = None
        for line in evaluation.split("\n"):
            line = line.strip()
            m = re.match(r"\*{0,2}Q(\d+)\*{0,2}:?\s*", line)
            if m:
                current_q = f"Q{m.group(1)}"
                lines_by_q[current_q] = lines_by_q.get(current_q, "") + " " + line
            elif current_q:
                lines_by_q[current_q] = lines_by_q.get(current_q, "") + " " + line

        for qid, content in lines_by_q.items():
            if "✅" in content and "ГОДНЫЙ" in content and qid in all_questions:
                approved.append(all_questions[qid][:150])

    # Дедупликация
    seen = set()
    return [q for q in approved if not (q.lower() in seen or seen.add(q.lower()))]

# ─── РАУНД 3: ДОБИВКА ──────────────────────────────────────────────────────

def round3_followup(topic: str, approved_questions: list, cfg: dict) -> dict:
    log.info(f"=== РАУНД 3: ДОБИВКА ({len(approved_questions)} вопросов, параллельно) ===")
    if not approved_questions:
        return {}
    tavily_key = cfg.get("TAVILY_API_KEY", "")
    def process(q: str, idx: int) -> tuple:
        key = f"q{idx}"
        # Смешанный поиск: Tavily + DuckDuckGo
        all_results = []
        for r in tavily_search(tavily_key, q, max_results=3):
            r["source"] = "tavily"
            all_results.append(r)
        try:
            from ddgs import DDGS
            for item in DDGS().text(q, max_results=3):
                all_results.append({"title": item.get("title",""), "url": item.get("href",""), "content": item.get("body",""), "raw_content": item.get("body",""), "source": "duckduckgo"})
        except:
            pass
        search_summary = ""
        seen = set()
        for j, r in enumerate(all_results, 1):
            url = r.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            c = (r.get("raw_content","") or r.get("content",""))[:2000]
            search_summary += f"\n--- Результат {j}: {r.get('title','')} [{r.get('source','')}] ---\nURL: {url}\n{c}\n"
        if not search_summary:
            search_summary = "(нет результатов)"
        prompt = PROMPT_ROUND3_FOLLOWUP.format(topic=topic, question=q, search_results=search_summary)
        messages = [{"role": "user", "content": prompt}]
        answer = None
        for kn in ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2", "MISTRAL_API_KEY_3"]:
            mk = cfg.get(kn, "")
            if mk:
                answer = call_mistral(mk, messages)
                if answer:
                    break
        return (key, {"question": q, "answer": answer or "(нет ответа)", "search_results": [{"title":r.get("title",""), "url":r.get("url",""), "source":r.get("source","")} for r in all_results[:6]]})
    answers = {}
    with ThreadPoolExecutor(max_workers=min(len(approved_questions), 5)) as executor:
        futures = {executor.submit(process, q, i): i for i, q in enumerate(approved_questions, 1)}
        for future in as_completed(futures, timeout=300):
            try:
                k, d = future.result(timeout=10)
                answers[k] = d
            except:
                pass
    log.info(f"Раунд 3: {len(answers)}/{len(approved_questions)}")
    return answers

# ─── РАУНД 4: СИНТЕЗ ────────────────────────────────────────────────────────

def round4_synthesis(topic: str, summaries: dict, questions_data: dict, followup_answers: dict, cfg: dict) -> Optional[str]:
    log.info("=== РАУНД 4: СИНТЕЗ (DeepSeek Pro) ===")
    agent_summaries = _build_summary_block(summaries)
    qa_parts = []
    if questions_data.get("questions"):
        for a_name, a_label, _ in AGENTS:
            q_text = questions_data["questions"].get(a_name)
            if q_text:
                qa_parts.append(f"### Вопросы от {a_label}:\n{q_text}\n")
    if followup_answers:
        qa_parts.append("### Ответы:\n")
        for _, qdata in followup_answers.items():
            qa_parts.append(f"**Вопрос:** {qdata.get('question','')}\n**Ответ:** {qdata.get('answer','')}\n")
    qa_section = "\n".join(qa_parts) or "(нет)"
    dead = [a[1] for a in AGENTS if not summaries.get(a[0])]
    dead_str = "\n".join(f"- {d}" for d in dead) if dead else "(все ответили)"
    prompt = PROMPT_ROUND4_SYNTHESIS.format(topic=topic, date=datetime.now().strftime("%Y-%m-%d %H:%M"), agent_summaries=agent_summaries, qa_section=qa_section, dead_agents=dead_str)
    messages = [{"role": "system", "content": "Ты — DeepSeek Pro, главный аналитик. Составляй отчёты на русском."}, {"role": "user", "content": prompt}]
    report = call_deepseek(cfg.get("DEEPSEEK_API_KEY", ""), messages, timeout=180)
    log.info(f"Отчёт: {len(report or '')} символов")
    return report or "# Ошибка синтеза"

# ─── СОХРАНЕНИЕ ──────────────────────────────────────────────────────────────

def save_results(topic: str, summaries: dict, questions_data: dict, followup_answers: dict, report: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9а-яА-Я_-]", "_", topic)[:40]
    out = OUTPUT_BASE / f"{ts}_{safe}"
    out.mkdir(parents=True, exist_ok=True)
    # Round 1
    with open(out / "round1_summaries.json", "w", encoding="utf-8") as f:
        json.dump({a[0]: ({"agent": a[0], "label": a[1], "role": a[2], "summary": (summaries.get(a[0]) or {}).get("summary")} if summaries.get(a[0]) else {"agent": a[0], "label": a[1], "summary": None, "error": "не ответил"}) for a in AGENTS}, f, ensure_ascii=False, indent=2)
    # Round 2
    with open(out / "round2_questions.json", "w", encoding="utf-8") as f:
        json.dump({**{a: {"agent": a, "questions": q} for a, q in (questions_data.get("questions") or {}).items()}, "evaluation": questions_data.get("evaluation", "")}, f, ensure_ascii=False, indent=2)
    # Round 3
    with open(out / "round3_answers.json", "w", encoding="utf-8") as f:
        json.dump(followup_answers, f, ensure_ascii=False, indent=2)
    # Report
    with open(out / "final_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    return out / "final_report.md"

def generate_html_report(topic: str, out_dir: Path, summaries: dict, questions_data: dict, followup_answers: dict, report: str) -> Path:
    agent_cards = ""
    for a_name, a_label, a_role in AGENTS:
        if summaries.get(a_name):
            s = summaries[a_name]["summary"]
            snip = s[:200].replace("\n", " ").replace("'", "&#39;")
            st = "✅"
            cls = "done"
        else:
            snip = "не ответил"
            st = "❌"
            cls = "dead"
        role_icon = {"tavily_broad": "🔍", "duckduckgo": "🦆", "server_search": "💻", "tavily_narrow": "🎯"}.get(a_role, "🔍")
        agent_cards += f"""<div class="agent-card {cls}"><div class="agent-header"><span class="agent-status">{st}</span><span class="agent-name">{a_label}</span><span class="agent-type">{role_icon}</span></div><div class="agent-snippet">{snip}</div></div>"""
    debate_lines = ""
    if questions_data.get("questions"):
        for a_name, a_label, _ in AGENTS:
            q = questions_data["questions"].get(a_name)
            if q:
                for line in q.strip().split("\n"):
                    if line.strip().startswith("Q") and ":" in line:
                        debate_lines += f"""<div class="debate-entry agent-{a_name}"><div class="debate-speaker">{a_label}</div><div class="debate-text">{line.strip().replace("'","&#39;")}</div></div>"""
    qa_lines = ""
    if followup_answers:
        for _, qd in followup_answers.items():
            qa_lines += f"""<div class="qa-entry"><div class="qa-question">🎯 {qd.get('question','')[:100].replace("'","&#39;")}</div><div class="qa-answer">{qd.get('answer','')[:300].replace("'","&#39;").replace(chr(10)," ")}</div></div>"""
    vhtml = report.replace("\n","<br>")
    vhtml = re.sub(r"## (.+?)<br>",r"<h2>\1</h2>",vhtml)
    vhtml = re.sub(r"### (.+?)<br>",r"<h3>\1</h3>",vhtml)
    vhtml = vhtml.replace("'","&#39;")
    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Глубокое исследование — {topic[:50]}</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0a0a0f;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:20px}}.container{{max-width:900px;margin:0 auto}}h1{{font-size:1.5em;color:#fff;margin-bottom:5px}}.meta{{color:#888;font-size:0.85em;margin-bottom:20px}}.agents-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:24px}}.agent-card{{background:#141420;border-radius:10px;padding:14px;border:1px solid #222}}.agent-card.done{{border-color:#1a4a1a}}.agent-card.dead{{border-color:#4a1a1a;opacity:.5}}.agent-header{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}.agent-status{{font-size:1.1em}}.agent-name{{font-weight:600;color:#fff;font-size:0.9em}}.agent-type{{font-size:0.7em;color:#666;margin-left:auto}}.agent-snippet{{font-size:0.78em;color:#aaa;line-height:1.4}}h2{{font-size:1.1em;color:#fff;margin:24px 0 12px;padding-bottom:6px;border-bottom:1px solid #222}}.debate-entry{{background:#141420;border-radius:8px;padding:10px 14px;margin-bottom:8px;border-left:3px solid #444}}.debate-speaker{{font-weight:600;font-size:0.8em;color:#888;margin-bottom:4px}}.debate-text{{font-size:0.85em;line-height:1.4}}.qa-entry{{background:#141420;border-radius:8px;padding:10px 14px;margin-bottom:8px}}.qa-question{{font-weight:600;font-size:0.85em;color:#7af;margin-bottom:4px}}.qa-answer{{font-size:0.82em;color:#ccc;line-height:1.4}}.verdict{{background:#0d1a0d;border-radius:10px;padding:16px;margin-top:16px;border:1px solid #1a3a1a;font-size:0.85em;line-height:1.6;color:#ccc}}.verdict h2{{color:#5f5}}.footer{{text-align:center;color:#444;font-size:0.75em;margin-top:30px}}
</style></head><body><div class="container">
<h1>🔬 {topic[:80]}</h1><div class="meta">Глубокое исследование · {datetime.now().strftime("%d.%m.%Y %H:%M")}</div>
<h2>🤖 Агенты</h2><div class="agents-grid">{agent_cards}</div>
<h2>💬 Дебаты</h2>{debate_lines or '<p style="color:#555">Нет данных</p>'}
<h2>🎯 Добивка</h2>{qa_lines or '<p style="color:#555">Нет вопросов</p>'}
<h2>🧠 Вердикт DeepSeek Pro</h2><div class="verdict">{vhtml}</div>
<div class="footer">Контент-завод «Зинаида»</div>
</div></body></html>"""
    p = out_dir / "report.html"
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    return p

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    if not topic:
        print("Ошибка: нет темы", file=sys.stderr)
        sys.exit(1)
    log.info("="*60)
    log.info(f"ГЛУБОКОЕ ИССЛЕДОВАНИЕ: {topic}")
    log.info("="*60)
    cfg = load_config()

    t0 = time.time()
    summaries = round1_parallel(topic, cfg)
    t1 = time.time()
    questions_data = round2_questions(topic, summaries, cfg)
    t2 = time.time()
    approved = parse_approved_questions(questions_data.get("evaluation", ""), questions_data.get("questions", {}))
    log.info(f"Годных вопросов: {len(approved)}")
    followup_answers = round3_followup(topic, approved, cfg)
    t3 = time.time()
    report_text = round4_synthesis(topic, summaries, questions_data, followup_answers, cfg)
    t4 = time.time()
    report_path = save_results(topic, summaries, questions_data, followup_answers, report_text or "# Ошибка")
    html_path = generate_html_report(topic, report_path.parent, summaries, questions_data, followup_answers, report_text or "# Ошибка")

    print(f"\n{'='*60}")
    print(f"ИССЛЕДОВАНИЕ ЗАВЕРШЕНО")
    print(f"Тема: {topic}")
    print(f"Отчёт: {report_path}")
    print(f"Визуализация: {html_path}")
    print(f"Время: R1={t1-t0:.0f}с R2={t2-t1:.0f}с R3={t3-t2:.0f}с R4={t4-t3:.0f}с")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
