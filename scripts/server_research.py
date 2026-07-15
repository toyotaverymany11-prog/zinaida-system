#!/usr/bin/env python3
"""
server_research.py — Исследование №2: 4 агента идут по серверу.

Каждый агент шерстит свою базу и приносит всё что есть по теме.
Используется ПОСЛЕ черновика (между Шагом 7 и 8).

Запуск:
  python3 server_research.py "тема поста" --instrument "Телепат"
  → сохраняет в /opt/zinaida/memory/server_research_latest.txt

Агенты:
  Агент 1: phases.db — фаза, боль, хук, триггер
  Агент 2: smm_rag.db — научные чанки, факты
  Агент 3: statistics + mechanics — цифры, статистика
  Агент 4: pisatel/ + CTA + hooks — готовые шаблоны и примеры
"""

import argparse
import json
import sqlite3
import os
import re
from pathlib import Path
from datetime import datetime

BASE = Path("/opt/zinaida")
INBOX = BASE / "inbox/PROJECTS/Otnoshenya"
PISATEL = BASE / "projects/Otnoshenya/pisatel"
MEMORY = BASE / "memory"
STATS = INBOX / "stats/mechanics"
CTA = INBOX / "cta_library"
HOOKS = INBOX / "hooks"

PHASES_DB = INBOX / "phases.db"
RAG_DB = MEMORY / "smm_rag.db"


def search_phases_db(theme: str) -> str:
    """Агент 1: ищет подходящую фазу по теме"""
    if not PHASES_DB.exists():
        return "[phases.db не найдена]"
    
    keywords = theme.lower().split()
    results = []
    
    try:
        conn = sqlite3.connect(str(PHASES_DB), timeout=5)
        c = conn.cursor()
        
        for kw in keywords[:5]:
            if len(kw) < 3:
                continue
            c.execute(
                "SELECT phase_id, pain_point FROM phases WHERE pain_point LIKE ? LIMIT 5",
                (f"%{kw}%",)
            )
            for row in c.fetchall():
                results.append({
                    "phase_id": row[0],
                    "pain_point": row[1]
                })
        
        conn.close()
    except Exception as e:
        return f"  [Ошибка phases.db: {e}]"
    
    if not results:
        return "  Фаза не найдена. Поищи вручную: sqlite3 phases.db"
    
    out = []
    for r in results[:5]:
        out.append(f"  Фаза: {r['phase_id']}")
        out.append(f"  Боль: {r['pain_point'][:100]}")
        out.append("  (доп. поля не найдены в схеме)")
        out.append("")
    
    return "\n".join(out)


def search_rag_db(theme: str) -> str:
    """Агент 2: ищет в smm_rag.db по теме"""
    if not RAG_DB.exists():
        return "[smm_rag.db не найдена]"
    
    conn = sqlite3.connect(str(RAG_DB))
    c = conn.cursor()
    
    keywords = theme.lower().split()
    results = []
    
    try:
        for kw in keywords[:5]:
            if len(kw) < 3:
                continue
            c.execute(
                "SELECT content, project_name FROM smm_knowledge_fts "
                "WHERE content MATCH ? ORDER BY rank LIMIT 5",
                (kw,)
            )
            for row in c.fetchall():
                results.append({
                    "content": row[0][:300],
                    "source": row[1][:50] if row[1] else ""
                })
    except sqlite3.OperationalError as e:
        return f"  [Ошибка FTS: {e}]"
    
    conn.close()
    
    if not results:
        return "  RAG: ничего не найдено"
    
    out = [f"  Найдено чанков: {len(results)}"]
    for r in results[:3]:
        out.append(f"  [{r['source']}] {r['content'][:200]}")
        out.append("")
    
    return "\n".join(out)


def search_statistics(theme: str) -> str:
    """Агент 3: ищет статистику по теме"""
    stats_dir = "/opt/zinaida/inbox/PROJECTS/Otnoshenya/stats/mechanics"
    if not os.path.isdir(stats_dir):
        return "[stats/mechanics/ не найдена]"
    
    keywords = [kw for kw in theme.lower().split() if len(kw) >= 3]
    if not keywords:
        keywords = ["статистика"]
    
    # Быстрый поиск через grep (shell) — не открывает все файлы
    import subprocess
    results = []
    for kw in keywords[:3]:
        try:
            grep = subprocess.run(
                ["grep", "-ril", kw, stats_dir],
                capture_output=True, text=True, timeout=5
            )
            if grep.stdout:
                for fpath in grep.stdout.strip().split("\n"):
                    fname = os.path.basename(fpath)
                    if fname not in [r["file"] for r in results]:
                        try:
                            with open(fpath, 'rb') as fh:
                                raw = fh.read(300)
                            results.append({
                                "file": fname,
                                "content": raw.decode('utf-8', errors='replace')[:200]
                            })
                        except:
                            pass
        except (subprocess.TimeoutExpired, Exception):
            pass
        if len(results) >= 5:
            break
    
    if not results:
        return "  Статистика: ничего не найдено"
    
    out = [f"  Найдено файлов статистики: {len(results)}"]
    for r in results[:3]:
        out.append(f"  [{r['file']}]")
        out.append(f"  {r['content'][:200]}")
        out.append("")
    
    return "\n".join(out)
def search_templates(theme: str, instrument: str = "") -> str:
    """Агент 4: ищет CTA-шаблоны, хуки, форматы по теме"""
    results = []
    
    # CTA-шаблоны — по имени файла
    cta_dir = "/opt/zinaida/inbox/PROJECTS/Otnoshenya/cta_library"
    if os.path.isdir(cta_dir):
        scan_terms = ['молч', 'тишин', 'игнор', 'гостинг']
        if instrument:
            scan_terms.insert(0, instrument[:4].lower())
        try:
            for fname in sorted(os.listdir(cta_dir)):
                for term in scan_terms[:3]:
                    if term in fname.lower():
                        try:
                            with open(os.path.join(cta_dir, fname), 'rb') as fh:
                                c = fh.read(200).decode('utf-8', errors='replace')
                            results.append(f"  [CTA] {fname}: {c}")
                        except:
                            pass
                        break
        except:
            pass
    
    # Хуки
    hooks_tpl = "/opt/zinaida/inbox/PROJECTS/Otnoshenya/hooks/templates"
    if os.path.isdir(hooks_tpl):
        try:
            for fname in sorted(os.listdir(hooks_tpl))[:5]:
                try:
                    with open(os.path.join(hooks_tpl, fname), 'rb') as fh:
                        c = fh.read(200).decode('utf-8', errors='replace')
                    results.append(f"  [Хук] {fname}: {c}")
                except:
                    pass
        except:
            pass
    
    # Писательские файлы
    if os.path.isfile("/opt/zinaida/projects/Otnoshenya/pisatel/14_WRITER_FORMATION.md"):
        results.append("  [Писатель] НОВЫЙ КОНВЕЙЕР: 14_WRITER_FORMATION.md доступен")
    
    results.append("  ⚠️ Старые файлы (01-13) изолированы — не используются")
    
    if not results:
        return "  Шаблоны: ничего не найдено"
    return "\n".join(results)


def main():
    parser = argparse.ArgumentParser(description="Исследование №2: 4 агента на сервер")
    parser.add_argument("theme", help="Тема поста")
    parser.add_argument("--instrument", default="", help="Целевой инструмент (Телепат/Детектив и т.д.)")
    args = parser.parse_args()
    
    theme = args.theme
    instrument = args.instrument
    
    print("╔════════════════════════════════════════════════════╗")
    print("║   ИССЛЕДОВАНИЕ №2 — 4 АГЕНТА НА СЕРВЕР           ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"Тема: {theme}")
    if instrument:
        print(f"Инструмент: {instrument}")
    print()
    
    # Агент 1: phases.db
    print("[1/4] Агент: phases.db...")
    phases = search_phases_db(theme)
    print(phases)
    print()
    
    # Агент 2: smm_rag.db
    print("[2/4] Агент: smm_rag.db...")
    rag = search_rag_db(theme)
    print(rag)
    print()
    
    # Агент 3: statistics
    print("[3/4] Агент: statistics + mechanics...")
    stats = search_statistics(theme)
    print(stats)
    print()
    
    # Агент 4: templates
    print("[4/4] Агент: CTA + hooks + pisatel...")
    templates = search_templates(theme, instrument)
    print(templates)
    print()
    
    # Собираем результат
    result = f"""╔══════════════════════════════════════════╗
║  РЕЗУЛЬТАТ ИССЛЕДОВАНИЯ №2
║  Тема: {theme}
║  Инструмент: {instrument or "не указан"}
║  Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╚══════════════════════════════════════════╝

=== АГЕНТ 1: ФАЗЫ (phases.db) ===
{phases}

=== АГЕНТ 2: RAG-БАЗА (smm_rag.db) ===
{rag}

=== АГЕНТ 3: СТАТИСТИКА ===
{stats}

=== АГЕНТ 4: ШАБЛОНЫ ===
{templates}
"""
    
    output_path = MEMORY / "server_research_latest.txt"
    output_path.write_text(result, encoding='utf-8')
    print(f"✅ Результат сохранён: {output_path}")


if __name__ == "__main__":
    main()
