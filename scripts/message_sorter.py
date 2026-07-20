#!/usr/bin/env python3
"""
Классификатор — сортировщик входящих сообщений.
Определяет тип сообщения и раскладывает в нужные места.
Без LLM, без токенов, жёсткие правила.

Использование:
  python3 message_sorter.py "текст сообщения"
  echo "текст" | python3 message_sorter.py
"""

import sys, os, json, re, subprocess, urllib.request, sqlite3
from datetime import datetime
from pathlib import Path

MEMORY_PATH = Path("/root/.hermes/memories/MEMORY.md")
VAULT_DIR = Path("/opt/zinaida/vault")
TODOIST_TOKEN = ""
with open("/opt/zinaida/meta_agent/.env") as f:
    for line in f:
        if "TODOIST" in line and "=" in line:
            TODOIST_TOKEN = line.split("=", 1)[1].strip()

# Паттерны
TASK_PATTERNS = [
    r"\b(сделай|создай|добавь|напомни|запиши|отметь|купи|закажи|позвони|напиши|сходи|съезди|свари|приготовь)\b",
    r"\b(завтра|сегодня|через\s+\d+\s+(час|день|мин|недел))",
    r"\b(в\s+\d{1,2}[:\.]\d{2})\b",
    r"\bсозвон|встреч|звонок\b",
]
LINK_PATTERN = r"https?://[^\s,;)]+"
KEY_PATTERNS = [r"\b(ключ|токен|пароль|api.?key|secret|token)\b"]
FACT_PATTERNS = [
    r"\b(запомни\s+что|важно:\s|решили\s+что|договорились\s+что|факт:\s|кстати[,\s]|к слову[,\s])\b",
]
QUESTION_PATTERNS = [
    r"^(почему|зачем|как|что\s+такое|где|когда|кто)\b",
]
COMMAND_PATTERNS = [
    r"^(проверь|найди|открой|запусти|покажи|расскажи|почини|исправь)\b",
]


def classify(text: str) -> tuple:
    """Возвращает (тип, уверенность, детали)"""
    text_lower = text.lower().strip()

    # 1. Ключ — самый приоритетный
    # Защита от ложных срабатываний: проверяем что нет отрицания
    has_negation = re.search(r'\b(нет\s+|без\s+|не\s+нужен|не\s+работает)\b', text_lower)

    if not has_negation:
        # GitHub токены (ghp_, ghu_, ghs_, gho_)
        for word in text.split():
            w = word.strip(".,;:\"'")
            if w.startswith(("ghp_", "ghu_", "ghs_", "gho_")) and len(w) > 30:
                return ("КЛЮЧ", 0.95, {"value": w})
            # API ключи sk- или просто 32+ символов
            if (w.startswith(("sk-", "sk_")) or re.match(r'^[A-Za-z0-9]{32,}$', w)) and len(w) > 20:
                return ("КЛЮЧ", 0.9, {"value": w})

        if re.search(KEY_PATTERNS[0], text_lower):
            for word in text.split():
                w = word.strip(".,;:\"'")
                if len(w) > 20 and re.match(r'^[A-Za-z0-9_\-]+$', w):
                    return ("КЛЮЧ", 0.95, {"value": w})

    # 2. Ссылка
    urls = re.findall(LINK_PATTERN, text)
    if urls:
        if re.search(TASK_PATTERNS[0], text_lower):
            return ("ЗАДАЧА", 0.9, {"urls": urls})
        return ("ССЫЛКА", 0.9, {"urls": urls})

    # 3. Если есть И факт И задача — приоритет задачи (mixed)
    has_fact = any(re.search(p, text_lower) for p in FACT_PATTERNS)
    has_task = any(re.search(p, text_lower) for p in TASK_PATTERNS)
    if has_fact and has_task:
        return ("ЗАДАЧА", 0.75, {"note": "mixed"})

    # 4. Факт
    if has_fact:
        return ("ФАКТ", 0.7, {})

    # 5. Задача
    for p in TASK_PATTERNS:
        if re.search(p, text_lower):
            return ("ЗАДАЧА", 0.85, {})

    # 6. Вопрос
    for p in QUESTION_PATTERNS:
        if re.search(p, text_lower):
            return ("ВОПРОС", 0.7, {})

    # 7. Команда
    for p in COMMAND_PATTERNS:
        if re.search(p, text_lower):
            return ("КОМАНДА", 0.6, {})

    return ("НЕЯСНО", 0.0, {})


def save_task(text, details):
    """Создаёт задачу в Todoist"""
    if not TODOIST_TOKEN:
        return "❌ Нет Todoist токена"

    project_map = {
        "встреч|хирург|врач|гастро|зуб": "6h56qvRh3VM4Xjhh",
        "техник|роутер|codex|сервер|8005|8006|8007": "6h56qvJwXHW8hrCX",
        "дизайн|картинк|карусель|лого|шрифт": "6h56qvHh7xGwx2VG",
        "контент|пост|статья|написать|текст": "6h56qvGJgxHCxpH3",
        "стратег|план|анализ|исследован": "6h56qv93FFMMVj5V",
        "идея|может|хотел": "6h56qvPFwPr38JMr",
    }
    project_id = "6h56jRJW65QCxJFf"  # Inbox
    for key, pid in project_map.items():
        if re.search(key, text.lower()):
            project_id = pid
            break

    priority = 4
    if any(w in text.lower() for w in ["срочно", "важно", "критич"]):
        priority = 1
    elif any(w in text.lower() for w in ["завтра", "сегодня", "через час"]):
        priority = 2

    # Проверка дубликата
    req = urllib.request.Request("https://api.todoist.com/api/v1/tasks")
    req.add_header("Authorization", f"Bearer {TODOIST_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        tasks = data.get("results", []) if isinstance(data, dict) else data
        for t in tasks:
            if t.get("content", "").lower().strip() == text.lower().strip():
                return f"⏭ Уже есть задача: {text[:50]}"
    except:
        pass

    payload = json.dumps({
        "content": text,
        "project_id": project_id,
        "priority": priority,
    }).encode()

    req2 = urllib.request.Request("https://api.todoist.com/api/v1/tasks", data=payload, method="POST")
    req2.add_header("Authorization", f"Bearer {TODOIST_TOKEN}")
    req2.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req2, timeout=10):
            return f"✅ Задача создана: {text[:50]}"
    except Exception as e:
        return f"❌ Ошибка Todoist: {e}"


def save_link(text, details):
    urls = details.get("urls", [])
    if not urls:
        return "❌ Нет URL"
    topic = "link"
    for word in text.split()[:5]:
        if word not in urls and not word.startswith(("http", "@")):
            topic = re.sub(r'[^a-zа-я0-9]', '_', word.lower())[:30]
    fp = VAULT_DIR / "links" / f"{topic}_{datetime.now().strftime('%Y%m%d')}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w") as f:
        f.write(f"# {topic}\n\n**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**Контекст:** {text[:200]}\n\n")
        for u in urls:
            f.write(f"- {u}\n")
    return f"✅ Ссылка сохранена: {fp.name}"


def save_key(text, details):
    value = details.get("value", "")
    if not value:
        return "❌ Не удалось извлечь ключ"
    fp = VAULT_DIR / "keys" / f"key_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w") as f:
        f.write(f"# Ключ от {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Контекст:** {text[:300]}\n**Значение:** {value}\n")
    return f"✅ Ключ сохранён: {fp.name} (проверь сам)"


def save_fact(text, details):
    fact_line = f"{datetime.now().strftime('%d.%m')} {text[:200]}"
    try:
        with open(MEMORY_PATH, "r") as f:
            content = f.read()
        if text.lower()[:50] in content.lower():
            return f"⏭ Уже записано: {text[:50]}"
        with open(MEMORY_PATH, "w") as f:
            f.write(fact_line + "\n" + content)
    except:
        with open(MEMORY_PATH, "w") as f:
            f.write(fact_line + "\n")
    return f"✅ Факт записан в MEMORY.md"


def save_question(text, details):
    fp = VAULT_DIR / "refs" / f"question_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w") as f:
        f.write(f"# Вопрос от {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{text}\n")
    return f"❓ Вопрос сохранён в notes"


def main():
    text = ""
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()
    if not text:
        print("Классификатор: нет текста")
        return

    msg_type, confidence, details = classify(text)
    actions = {
        "ЗАДАЧА": save_task,
        "ССЫЛКА": save_link,
        "КЛЮЧ": save_key,
        "ФАКТ": save_fact,
        "ВОПРОС": save_question,
        "КОМАНДА": lambda t, d: f"👀 Команда: {t[:80]}",
        "НЕЯСНО": lambda t, d: f"🤷 Не поняла тип: {t[:80]}",
    }
    action = actions.get(msg_type, lambda t, d: f"❓ Неизвестный тип: {t[:80]}")
    result = action(text, details)
    print(f"[{msg_type}] (уверенность: {confidence:.0%})")
    print(result)


if __name__ == "__main__":
    main()
