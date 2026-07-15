#!/usr/bin/env python3
"""
Скрипт инициализации контекста для нового чата.
Запуск: python3 /opt/zinaida/scripts/init_context.py

Подгружает:
- Системный слепок (SYSTEM_SNAPSHOT.md)
- AGENTS.md (правила)
- Проекты (inbox/PROJECTS/*)
- phases.db (фазы отношений)
- smm_rag.db (база знаний)
- content_rotation.db (ротация)
- analytics.db (метрики)
- Mem0 (семантическая память)
- Сессии (история обсуждений)
- shared_memory/
"""

import json, sqlite3, subprocess, sys, os
from pathlib import Path

BASE = Path("/opt/zinaida")
PROJECTS = BASE / "inbox" / "PROJECTS"
MEMORY = BASE / "memory"
SHARED = BASE / "shared_memory"
SCRIPTS = BASE / "scripts"

def banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def read_file_head(path, max_lines=5):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [f.readline().strip() for _ in range(max_lines)]
            return " | ".join(l for l in lines if l)
    except: return "?"

def db_count(path, table=None):
    try:
        conn = sqlite3.connect(str(path))
        c = conn.cursor()
        if table:
            c.execute(f"SELECT COUNT(*) FROM {table}")
        else:
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            tables = c.fetchone()[0]
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            names = [r[0] for r in c.fetchall()]
            conn.close()
            return tables, names
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return "?"

def check_file(path):
    p = Path(path)
    return "✅" if p.exists() else "❌"

def find_project_dirs():
    projects = {}
    if PROJECTS.exists():
        for p in PROJECTS.iterdir():
            if p.is_dir():
                md_files = list(p.rglob("*.md"))
                projects[p.name] = len(md_files)
    return projects

def count_md(path, max_depth=3):
    path = Path(path)
    if not path.exists(): return 0
    return len(list(path.rglob("*.md")))

def get_mem0_memories():
    """Пытается получить Mem0 через MCP. Если не может — пропускает."""
    try:
        result = subprocess.run(
            ["python3", "-c", """
import json, sys
# Проверяем что Mem0 MCP сервер жив
try:
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", 9633, timeout=2)
    conn.request("GET", "/health")
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    print("mem0_alive")
except Exception as e:
    print(f"mem0_down: {e}")
"""], capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()
        if "mem0_alive" in output:
            return "✅ Mem0 MCP жив"
        return output[:100]
    except:
        return "❌ Mem0 не доступен"

def get_recent_sessions():
    try:
        result = subprocess.run(
            ["python3", "-c", """
import json, sys
try:
    # Check if session DB exists
    import sqlite3
    db_path = "/root/.hermes/session.db"
    if not __import__('os').path.exists(db_path):
        db_path = "/root/.hermes/sessions.db"
    if __import__('os').path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Try to count sessions
        c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        tables = c.fetchone()[0]
        if tables > 0:
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [r[0] for r in c.fetchall()]
            print(f"tables: {table_names}")
        conn.close()
    else:
        print("no_session_db")
except Exception as e:
    print(f"session_error: {e}")
"""], capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()
        return output[:100]
    except:
        return "❌"

def main():
    print("""
╔══════════════════════════════════════════════╗
║     ИНИЦИАЛИЗАЦИЯ КОНТЕКСТА — ЗИНАИДА       ║
║        11.07.2026  v1.0                      ║
╚══════════════════════════════════════════════╝
""")

    # 1. Системный слепок
    banner("1. СИСТЕМНЫЙ СЛЕПОК")
    snap = MEMORY / "SYSTEM_SNAPSHOT.md"
    if snap.exists():
        with open(snap, "r", encoding="utf-8") as f:
            first = f.readline().strip()
            date_line = f.readline().strip()
        print(f"  {first}")
        print(f"  {date_line}")
    else:
        print("  ❌ NOT FOUND")

    # 2. AGENTS.md
    banner("2. ПРАВИЛА (AGENTS.md)")
    agents = BASE / "AGENTS.md"
    if agents.exists():
        with open(agents, "r", encoding="utf-8") as f:
            lines = [f.readline().strip() for _ in range(8)]
        print(f"  {lines[0]}")
        print(f"  {lines[1]}")
        print(f"  Правило №0: {'✅' if 'Правило №0' in ''.join(lines) else '❌'}")

    # 3. Проекты
    banner("3. ПРОЕКТЫ")
    if PROJECTS.exists():
        for p in PROJECTS.iterdir():
            if p.is_dir():
                md = count_md(p)
                print(f"  ✅ {p.name}: {md} .md файлов")
    else:
        print("  ❌ Нет проектов")

    # 4. phases.db
    banner("4. ФАЗЫ ОТНОШЕНИЙ (phases.db)")
    db_path = PROJECTS / "Otnoshenya" / "phases.db"
    if db_path.exists():
        tables, names = db_count(db_path)
        print(f"  ✅ {tables} таблиц: {names[:5]}...")
        for t in names:
            cnt = db_count(db_path, t)
            if cnt != "?":
                print(f"     {t}: {cnt} записей")
    else:
        print("  ❌ NOT FOUND")

    # 5. RAG база
    banner("5. БАЗА ЗНАНИЙ (smm_rag.db)")
    rag_path = MEMORY / "smm_rag.db"
    if rag_path.exists():
        tables, names = db_count(rag_path)
        print(f"  ✅ {tables} таблиц: {names}")
    else:
        print("  ❌ NOT FOUND")

    # 6. content_rotation
    banner("6. РОТАЦИЯ (content_rotation.db)")
    rot_path = PROJECTS / "Otnoshenya" / "content_rotation.db"
    if rot_path.exists():
        tables, names = db_count(rot_path)
        print(f"  ✅ {tables} таблиц: {names}")
    else:
        print("  ❌ NOT FOUND")

    # 7. analytics
    banner("7. АНАЛИТИКА (analytics.db)")
    anal_path = MEMORY / "analytics.db"
    if anal_path.exists():
        tables, names = db_count(anal_path)
        print(f"  ✅ {tables} таблиц: {names}")
    else:
        print("  ❌ NOT FOUND")

    # 8. design_assets
    banner("8. ДИЗАЙН (design_assets.db)")
    design_path = MEMORY / "design_assets.db"
    if design_path.exists():
        tables, names = db_count(design_path)
        print(f"  ✅ {tables} таблиц: {names}")
    else:
        print("  ❌ NOT FOUND")

    # 9. Shared memory
    banner("9. ОБЩАЯ ПАМЯТЬ (shared_memory)")
    md_count = count_md(SHARED)
    print(f"  ✅ {md_count} .md файлов")

    # 10. Mem0
    banner("10. MEM0 (семантическая память)")
    print(f"  {get_mem0_memories()}")

    # 11. Роутеры
    banner("11. РОУТЕРЫ")
    routers = {
        8002: "Zinaida-Router",
        8003: "Zina2-Router",
        8005: "8005 v2.0 (Server RAG)"
    }
    for port, name in routers.items():
        try:
            import http.client
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            data = resp.read().decode()
            conn.close()
            status = json.loads(data).get("status", "?") if data else "?"
            print(f"  ✅ :{port} {name} — {status}")
        except:
            print(f"  ❌ :{port} {name} — не отвечает")

    # 12. Диагностика
    banner("12. ДИАГНОСТИКА")
    diag_path = SCRIPTS / "tech_diagnostic.py"
    if diag_path.exists():
        print(f"  ✅ tech_diagnostic.py — скрипт диагностики")
    else:
        print("  ❌ нет скрипта диагностики")

    print()
    print(f"╔{'═'*58}╗")
    print(f"║  ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА                                 ║")
    print(f"║  Прочитай AGENTS.md и BOOTSTRAP.md для полных правил    ║")
    print(f"╚{'═'*58}╝")
    print()

if __name__ == "__main__":
    main()
