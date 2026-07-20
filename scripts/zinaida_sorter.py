#!/usr/bin/env python3
"""
zinaida_sorter.py — Автоматический сортировщик информации
========================================================
Что делает:
1. Смотрит /opt/zinaida/inbox/raw/ на наличие новых файлов
2. Определяет тему по содержимому + названию + расширению
3. Раскладывает в соответствующую папку проекта
4. Пишет отчёт в updates_log.md
5. Обновляет память

Темы: marketing, product, legal, pisatel, design, tech, character
Запуск: вручную или через cron (каждые N сообщений в чате)

Использование:
  python3 /opt/zinaida/scripts/zinaida_sorter.py              # разобрать всё
  python3 /opt/zinaida/scripts/zinaida_sorter.py --file /path # разобрать конкретный файл
"""

import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

INBOX_RAW = "/opt/zinaida/inbox/raw"
INBOX_PROCESSED = "/opt/zinaida/inbox/processed"
UPDATES_LOG = "/opt/zinaida/shared_memory/updates_log.md"
PROJECT_DIR = "/opt/zinaida/projects/Otnoshenya"

# Карта: ключевые слова → папка назначения
TOPIC_MAP = [
    ("marketing", ["маркет", "воронк", "funnel", "smm", "соцсет", "продвиж",
                   "конверси", "трафик", "лид", "реклам", "saves", "shares",
                   "cta", "позиционир", "таргет", "аудитор", "инструмент",
                   "профайлер", "предиктор", "дуэль", "сканер", "досье",
                   "экспертиз", "токен", "подписк", "тариф", "монетизац"]),
    ("product", ["продукт", "система", "лаб", "лаборатор", "память",
                 "technology", "функционал", "архитектур", "юнит-эконом",
                 "readiness", "ограничен"]),
    ("legal", ["юрид", "legal", "152-фз", "дисклеймер", "безопасн",
               "claims", "персональн"]),
    ("pisatel", ["писател", "пост", "стиль", "шквальн", "копрайт",
                 "креатив", "референс", "conтент-план", "карусел",
                 "алгоритм", "платформ", "рубрик"]),
    ("design", ["дизайн", "визуал", "lora", "изображен", "картинк",
                "аватар", "обложк", "презент", "шаблон", "шрифт"]),
    ("tech", ["техник", "сервер", "docker", "провайдер", "роутер",
              "api", "порт", "система", "config", "баг", "ошибк",
              "установк", "разверт"]),
    ("character", ["персонаж", "зинаид", "характер", "личность",
                   "голос", "тон", "днк"]),
]

def detect_topic(content: str, filename: str):
    """Определяет тему по содержимому и имени файла. Возвращает тему или None."""
    text = (content + " " + filename).lower()
    scores = {}
    for topic, keywords in TOPIC_MAP:
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[topic] = score
    if scores:
        best_topic = max(scores, key=lambda k: scores[k])
        return best_topic
    return None

def process_file(filepath: str) -> dict:
    """Обрабатывает один файл: определяет тему, копирует в папку, логирует"""
    path = Path(filepath)
    if not path.exists():
        return {"status": "error", "reason": "not_found", "file": filepath}

    content = path.read_text(encoding="utf-8", errors="replace")[:5000]
    topic = detect_topic(content, path.name)

    result = {
        "status": "processed" if topic else "unknown",
        "file": filepath,
        "topic": topic or "unknown",
        "name": path.name,
        "size": path.stat().st_size,
    }

    if topic:
        dest_dir = f"{PROJECT_DIR}/{topic}"
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = f"{dest_dir}/{path.name}"
        # Если файл с таким именем уже есть — добавляем дату
        if os.path.exists(dest_path):
            name_stem = path.stem
            name_ext = path.suffix
            dest_path = f"{dest_dir}/{name_stem}_{datetime.now().strftime('%Y%m%d')}{name_ext}"
        shutil.copy2(filepath, dest_path)
        result["dest"] = dest_path
        # Перемещаем в processed
        proc_path = f"{INBOX_PROCESSED}/{path.name}"
        shutil.move(filepath, proc_path)
        result["moved_to"] = proc_path
    else:
        result["note"] = "Тема не определена, файл остаётся в raw/"

    return result

def write_log(results: list):
    """Пишет отчёт в updates_log.md"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    total = len(results)
    processed = [r for r in results if r["status"] == "processed"]
    unknown = [r for r in results if r["status"] == "unknown"]

    log_entry = f"\n## {today} — СОРТИРОВЩИК РАЗОБРАЛ {total} ФАЙЛОВ\n"
    log_entry += f"- Обработано: {len(processed)}\n"
    for r in processed:
        log_entry += f"  ✅ {r['name']} → {r['topic']}/ ({r['dest']})\n"
    if unknown:
        log_entry += f"- Не определено: {len(unknown)} (остались в raw/)\n"
        for r in unknown:
            log_entry += f"  ❓ {r['name']}\n"
    log_entry += f"- Статус: проведён в {now}\n"

    with open(UPDATES_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

def main():
    files = list(Path(INBOX_RAW).iterdir()) if Path(INBOX_RAW).exists() else []
    md_files = [f for f in files if f.suffix in ('.md', '.txt', '.json', '.yaml', '.csv', '.pdf')]

    if not md_files:
        print("📭 inbox/raw/ пуста. Нечего сортировать.")
        return

    print(f"📥 Найдено {len(md_files)} файлов. Сортирую...")
    results = []
    for f in md_files:
        result = process_file(str(f))
        results.append(result)
        icon = "✅" if result["status"] == "processed" else "❓"
        print(f"  {icon} {result['name']} → {result.get('topic', '?')}")

    write_log(results)
    print(f"📝 updates_log.md обновлён.")

if __name__ == "__main__":
    main()
