#!/usr/bin/env python3
"""
deep_research_orchestrator.py — программа-интерфейс для глубокого исследования.

Режимы работы:
1. Без аргументов: интерактивный диалог — задаёт вопросы, уточняет тему
2. С аргументом:  python3 deep_research_orchestrator.py "тема исследования"
   — запускает deep_research.py с темой сразу

После завершения показывает путь к отчёту.
"""

import os
import sys
import json
import time
import subprocess
import re
from datetime import datetime
from pathlib import Path

# ─── КОНСТАНТЫ ───────────────────────────────────────────────────────────────

DEEP_RESEARCH_SCRIPT = "/opt/zinaida/scripts/deep_research.py"
OUTPUT_BASE = Path("/opt/zinaida/sandbox/deep_research")
HISTORY_FILE = OUTPUT_BASE / "research_history.json"

HEADER = """
╔══════════════════════════════════════════════════════════════╗
║           ГЛУБОКОЕ ИССЛЕДОВАНИЕ — Deep Research            ║
║  4 агента (Mistral + GitHub + Ollama + DeepSeek Pro)       ║
║  4 раунда: Сбор → Вопросы → Добивка → Синтез               ║
╚══════════════════════════════════════════════════════════════╝
"""

QUESTIONS = [
    {
        "id": "topic",
        "question": "Какая тема исследования?",
        "hint": "(опиши кратко — я уточню если нужно)",
        "required": True,
    },
    {
        "id": "goal",
        "question": "Что конкретно хочешь узнать?",
        "hint": "(цифры, факты, сравнение, анализ, причины — что важно?)",
        "required": False,
    },
    {
        "id": "depth",
        "question": "Какая глубина нужна?",
        "hint": "(1 — быстрый обзор / 2 — детальный разбор / 3 — максимальный, с противоречиями)",
        "required": False,
    },
    {
        "id": "sources",
        "question": "Есть дополнительные источники или файлы?",
        "hint": "(ссылки, файлы, свои заметки — вставь сюда)",
        "required": False,
    },
]


def print_header():
    print(HEADER)
    print(f"  Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()


def ask_questions_interactive() -> dict:
    """Интерактивный опрос. Возвращает словарь с ответами."""
    answers = {}

    for q in QUESTIONS:
        print()
        print(f"❓ {q['question']}")
        print(f"   {q['hint']}")
        print("   (Enter — пропустить)" if not q["required"] else "   (обязательно)")
        print()

        user_input = ""
        # Читаем многострочный ввод до пустой строки или ---
        print(">>> ", end="", flush=True)
        for line in sys.stdin:
            line = line.rstrip("\n\r")
            if line.strip() == "---" or (line.strip() == "" and user_input):
                break
            if not line.strip() and not user_input:
                # Если пустая строка в начале — значит пропускаем
                break
            user_input += line + "\n"

        user_input = user_input.strip()

        if q["required"] and not user_input:
            print("   ⚠️  Это обязательный вопрос. Попробуй ещё раз:")
            continue

        if user_input:
            answers[q["id"]] = user_input
        else:
            if q["id"] == "depth":
                answers[q["id"]] = "2"  # по умолчанию детальный
            elif q["id"] == "sources":
                answers[q["id"]] = ""
            else:
                answers[q["id"]] = ""

    return answers


def prepare_topic(answers: dict) -> str:
    """Из ответов формирует тему для deep_research.py."""
    topic = answers.get("topic", "")

    goal = answers.get("goal", "")
    depth = answers.get("depth", "2")
    sources = answers.get("sources", "")

    # Если есть цель — добавляем в тему для контекста
    if goal:
        topic = f"{topic}. Цель: {goal}"

    # Глубина влияет на количество результатов поиска
    if depth == "3":
        topic = f"{topic}. [максимальная глубина]"
    elif depth == "1":
        topic = f"{topic}. [быстрый обзор]"

    # Если есть свои источники — добавляем
    if sources:
        topic = f"{topic}. Дополнительные материалы: {sources[:200]}"

    return topic


def save_history(topic: str, report_path: str):
    """Сохраняет историю исследований."""
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "report_path": str(report_path),
    }

    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except:
            history = []

    history.append(entry)

    # Храним последние 20
    if len(history) > 20:
        history = history[-20:]

    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def show_recent_history(limit: int = 3):
    """Показывает последние исследования."""
    if not HISTORY_FILE.exists():
        return

    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not history:
            return

        print()
        print("📋 Последние исследования:")
        for entry in history[-limit:]:
            t = entry.get("timestamp", "")[:16]
            topic = entry.get("topic", "")[:60]
            print(f"   [{t}] {topic}")
    except:
        pass


def run_deep_research(topic: str) -> str:
    """Запускает deep_research.py и возвращает путь к отчёту."""
    print()
    print("═" * 60)
    print("🚀 ЗАПУСК ГЛУБОКОГО ИССЛЕДОВАНИЯ")
    print(f"   Тема: {topic[:80]}..." if len(topic) > 80 else f"   Тема: {topic}")
    print(f"   Время: ~2-3 минуты")
    print("═" * 60)
    print()
    print("   Запускаю 4 агентов: Mistral + GitHub + Ollama + Mistral2")
    print("   Раунд 1: сбор информации...")
    print()

    # Запускаем deep_research.py
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, DEEP_RESEARCH_SCRIPT, topic],
            capture_output=True,
            text=True,
            timeout=3600,  # час максимум
        )

        elapsed = time.time() - start_time
        print(f"   ✅ Исследование завершено за {elapsed:.0f} сек")
        print()

        # Ищем путь к отчёту в выводе
        output = result.stdout + result.stderr
        report_path = ""
        for line in output.split("\n"):
            if "Отчёт:" in line and ".md" in line:
                m = re.search(r"Отчёт:\s*(/\S+\.md)", line)
                if m:
                    report_path = m.group(1)
                    break

        if report_path:
            print(f"   📄 Отчёт: {report_path}")
            # Ищем .html файл рядом
            html_file = str(report_path).replace(".md", ".html")
            if os.path.exists(html_file):
                print(f"   🖥️  Визуализация: {html_file}")
            return report_path
        else:
            print("   ⚠️ Путь к отчёту не найден в выводе")
            print()
            print("--- Вывод скрипта (последние 20 строк) ---")
            lines = output.strip().split("\n")
            for line in lines[-20:]:
                print(f"  {line}")
            return ""

    except subprocess.TimeoutExpired:
        print("   ❌ Исследование прервано по таймауту (10 мин)")
        return ""
    except Exception as e:
        print(f"   ❌ Ошибка запуска: {e}")
        return ""


def show_report_summary(report_path: str):
    """Показывает краткую выжимку отчёта."""
    if not report_path or not os.path.exists(report_path):
        print("   ⚠️ Отчёт не найден")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Выдираем ключевые разделы
    sections = re.findall(r"## \d+\.\s*(.+?)\n(.+?)(?=\n##|\Z)", content, re.DOTALL)

    print()
    print("═" * 60)
    print("📊 КРАТКАЯ ВЫЖИМКА ОТЧЁТА")
    print("═" * 60)

    for title, body in sections[:3]:
        title = title.strip()
        # Берём первые 3-5 строк
        lines = [l.strip() for l in body.strip().split("\n") if l.strip()]
        preview = "\n".join(lines[:5])
        print(f"\n### {title}")
        print(f"   {preview[:300]}...")

    print()
    print(f"📄 Полный отчёт: {report_path}")
    print()


def main():
    # Проверяем аргументы
    if len(sys.argv) > 1:
        # Прямой запуск с темой
        topic = " ".join(sys.argv[1:])
        print_header()
        print(f"📌 Тема: {topic}")
        print()

        report_path = run_deep_research(topic)
        if report_path:
            save_history(topic, report_path)
            show_report_summary(report_path)

        return
    else:
        # Загружаем последние темы
        pass

    # Интерактивный режим — задаём вопросы
    print_header()

    # Показываем последние исследования
    show_recent_history()

    print("Я задам несколько вопросов, чтобы уточнить тему.")
    print("Отвечай развёрнуто. Когда закончишь — напиши '---' на новой строке или дважды Enter.")
    print("Если хочешь прервать — напиши 'отмена'.")
    print()

    # Задаём вопросы
    answers = ask_questions_interactive()

    if not answers.get("topic"):
        print("\n❌ Тема не указана. Исследование отменено.")
        sys.exit(1)

    topic = prepare_topic(answers)

    print()
    print(f"📌 Итоговая тема: {topic[:80]}...")
    print()

    # Финальное подтверждение
    print("Запускаем исследование? (Enter = да, 'нет' = отмена)")
    try:
        confirm = sys.stdin.readline().strip().lower()
    except:
        confirm = ""

    if confirm in ("нет", "н", "no", "n"):
        print("\n❌ Исследование отменено.")
        sys.exit(0)

    # Запуск
    report_path = run_deep_research(topic)
    if report_path:
        save_history(topic, report_path)
        show_report_summary(report_path)

    print()
    print("═" * 60)
    print("💡 Чтобы повторить: python3 deep_research_orchestrator.py")
    print("   Или сразу: python3 deep_research_orchestrator.py \"тема\"")
    print("═" * 60)

    # Telegram notification
    import os as _os
    _os.system(f"python3 /opt/zinaida/telegram_bot/notify.py '✅ Глубокое исследование завершено. Отчёт: {report_path}' 2>/dev/null &")


if __name__ == "__main__":
    main()
