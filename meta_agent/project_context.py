import os
import sys
import glob
import json
import hashlib
import warnings
from datetime import datetime

sys.path.insert(0, '/opt/zinaida/meta_agent')
from memory_router import search_facts, save_fact
from web_tools import search_web

warnings.filterwarnings("ignore")

MEMORY_DIR = "/opt/zinaida/memory"
PROJECTS_DIR = f"{MEMORY_DIR}/projects"
MAX_CTX_BYTES = 6 * 1024
LOG_PATH = "/opt/zinaida/logs/web_events.jsonl"
ENV_PATH = "/opt/zinaida/.env"
PENDING_DIR = "/opt/zinaida/inbox/research_pending"

def _get_env(var, default=""):
    if not os.path.exists(ENV_PATH):
        return default
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == var:
                    return v.strip()
    return default

DRY_RUN = _get_env("DEEP_RESEARCH_DRY_RUN", "true").lower() == "true"

def _log_web_event(event):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _calc_trust_score(snippet, project):
    score = 0.0
    url = snippet.get("url", "")
    trusted_domains = ["github.com", "arxiv.org", ".gov", ".edu", "stackoverflow.com", "python.org", "habr.com", "opennet.ru"]
    if any(d in url for d in trusted_domains):
        score += 0.4
    if url:
        score += 0.2
    niche_keywords = {
        "villa_sales": ["вилла", "сочи", "недвижимость", "аренда", "сделка", "цена"],
        "otnosheniya": ["отношения", "психология", "эмоции", "границы", "доверие"],
        "global": [],
        "system": ["система", "зинаида", "hermes", "обновление", "установили", "версия", "память", "код"]
    }
    keywords = niche_keywords.get(project, [])
    if keywords and any(k in snippet.get("snippet", "").lower() for k in keywords):
        score += 0.3
    elif not keywords:
        score += 0.3
    return score

def _calc_research_score(user_text, facts, web_res):
    score = 0
    if not facts and not web_res:
        score += 4
    if len(user_text) > 150:
        score += 1
    research_markers = ["анализ рынка", "техническое сравнение", "долгосрочные перспективы",
                        "стратегическое планирование", "прогноз на", "тенденции",
                        "сравнить", "динамика", "исследование"]
    if any(m in user_text.lower() for m in research_markers):
        score += 2
    freshness_markers = ["2024", "2025", "2026", "последние", "актуальные", "текущий год", "новый"]
    if any(m in user_text.lower() for m in freshness_markers):
        score += 2
    return score

def _generate_research_brief(user_text, project):
    words = user_text.split()
    goal = " ".join(words[:15])
    scope = []
    research_markers = ["анализ", "сравнение", "перспективы", "планирование", "прогноз", "тенденции", "динамика"]
    for m in research_markers:
        if m in user_text.lower():
            scope.append(m)
    if not scope:
        scope = ["обзор", "ключевые факты", "источники"]
    brief = {
        "task": "Техническое задание",
        "goal": goal,
        "scope": scope[:5],
        "constraints": {
            "sources": ["официальная документация", "научные статьи", "проверенные источники"],
            "time_limit_hours": 4,
            "output_format": "PDF"
        },
        "context": f"Проект: {project}. Запрос требует глубокого анализа."
    }
    return brief

def _is_system_query(user_text):
    lower = user_text.lower()
    markers = [
        "что сегодня установили", "какая версия", "что нового в системе",
        "твое состояние", "как ты устроена", "какие у тебя функции",
        "что тебе добавили", "твоя память", "системное обновление",
        "зинаида версия", "hermes обновление", "что изменилось в тебе"
    ]
    return any(m in lower for m in markers)

def _is_short_or_greeting(user_text):
    lower = user_text.lower().strip()
    if len(lower) < 15:
        return True
    greetings = ["привет", "здравствуй", "добрый день", "доброе утро", "добрый вечер", "хай", "hello", "hi", "ку"]
    if any(g in lower for g in greetings) and len(lower.split()) <= 3:
        return True
    return False

def _handle_memory_marker(user_text):
    lower = user_text.lower()
    if "[запомни:" in lower or "[memory:" in lower:
        marker = "[запомни:" if "[запомни:" in lower else "[memory:"
        start = lower.find(marker) + len(marker)
        content = user_text[start:].strip().rstrip("]").strip()
        if content:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_fact(content, "chat_marker", "global", current_time)
            return f"[MEMORY_SAVED] Факт сохранён в глобальную память: {content}. Подтверди пользователю кратко."
    return None

def load_project_context(user_text: str) -> str:
    try:
        marker_res = _handle_memory_marker(user_text)
        if marker_res:
            return marker_res

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_block = f"[CURRENT_TIME] Сейчас: {current_time}\n"

        is_system = _is_system_query(user_text)
        is_greeting = _is_short_or_greeting(user_text)

        project = "global"
        upper = user_text.upper()
        if "[PROJECT:" in upper:
            start = upper.find("[PROJECT:") + 9
            end = upper.find("]", start)
            if end > start:
                project = user_text[start:end].strip().lower()
        else:
            keywords_map = {"вилла": "villa_sales", "недвижимость": "villa_sales", "отношения": "otnosheniya", "психология": "otnosheniya", "код": "dev_experience", "ошибк": "dev_experience", "python": "dev_experience", "bash": "dev_experience", "терминал": "dev_experience", "heredoc": "dev_experience", "sqlite": "dev_experience", "деплой": "dev_experience", "роутер": "dev_experience", "systemd": "dev_experience", "api": "dev_experience", "навык": "dev_experience", "опыт": "dev_experience", "баг": "dev_experience", "фикс": "dev_experience", "протокол": "dev_experience", "docker": "dev_experience", "caddy": "dev_experience", "git": "dev_experience", "cron": "dev_experience"}
            for kw, pid in keywords_map.items():
                if kw in user_text.lower():
                    project = pid
                    break

        if is_system:
            project = "system"

        ctx_parts = [time_block]

        brief_path = os.path.join(PROJECTS_DIR, project, "context", "brief.md")
        if os.path.exists(brief_path):
            with open(brief_path, "r", encoding="utf-8", errors="ignore") as f:
                ctx_parts.append("BRIEF:\n" + f.read()[:2048])

        skills_path = os.path.join(PROJECTS_DIR, project, "skills", "active")
        if os.path.isdir(skills_path):
            skill_files = sorted(glob.glob(os.path.join(skills_path, "*.md")), key=os.path.getmtime, reverse=True)[:2]
            skill_ctx = "\n".join([open(fp, "r", encoding="utf-8", errors="ignore").read() for fp in skill_files])
            ctx_parts.append("SKILLS:\n" + skill_ctx[:2048])

        facts = search_facts(user_text, project, 5)
        has_facts = bool(facts)
        if has_facts:
            ctx_parts.append("FACTS:\n" + "\n---\n".join(facts)[:2048])

        web_res = []
        if not has_facts and not is_system and not is_greeting:
            web_res = search_web(user_text, 3)
            if web_res:
                web_text_parts = []
                saved_count = 0
                for r in web_res:
                    trust = _calc_trust_score(r, project)
                    action = "ignored"
                    if trust >= 0.7 and saved_count < 2:
                        content_hash = hashlib.sha256(f"{r.get('snippet','')}|{r.get('url','')}".encode()).hexdigest()
                        saved = save_fact(r.get("snippet",""), r.get("url",""), project, current_time, content_hash)
                        action = "saved" if saved else "duplicate"
                        if saved:
                            saved_count += 1
                    else:
                        action = "used" if trust >= 0.5 else "ignored"

                    _log_web_event({
                        "timestamp": current_time,
                        "query": user_text[:100],
                        "source": r.get("url",""),
                        "trust_score": trust,
                        "action": action
                    })
                    if trust >= 0.5:
                        web_text_parts.append(f"[WEB_SOURCE] {r['title']}: {r['snippet'][:300]} ({r['url']})")

                if web_text_parts:
                    ctx_parts.append("WEB_SOURCES:\n" + "\n".join(web_text_parts)[:1500])

        research_score = _calc_research_score(user_text, facts, web_res)
        if research_score >= 7 and not is_system:
            brief = _generate_research_brief(user_text, project)
            if DRY_RUN:
                ctx_parts.append(f"[DEEP_RESEARCH_DRY_RUN] Score: {research_score}. Brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}")
            else:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                req_file = os.path.join(PENDING_DIR, f"request_{ts}.json")
                with open(req_file, "w", encoding="utf-8") as f:
                    json.dump(brief, f, ensure_ascii=False, indent=2)
                ctx_parts.append(f"[DEEP_RESEARCH_REQUIRED] Score: {research_score}. Файл ТЗ: {req_file}")

        full_ctx = "\n\n".join(ctx_parts)
        ctx_bytes = full_ctx.encode("utf-8")
        if len(ctx_bytes) > MAX_CTX_BYTES:
            full_ctx = ctx_bytes[:MAX_CTX_BYTES].decode("utf-8", "ignore") + "\n[КОНТЕКСТ ОБРЕЗАН ПО ЛИМИТУ]"

        if not has_facts and not any("WEB_SOURCE" in p for p in ctx_parts) and research_score < 7 and not is_system:
            full_ctx = "[CONTEXT_INSUFFICIENT]\n" + full_ctx

        return full_ctx
    except Exception as e:
        return f"[ОШИБКА КОНТЕКСТА: {e}]"
