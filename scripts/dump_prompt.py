#!/usr/bin/env python3
import sys
import os
import sqlite3
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, '/opt/zinaida/yadro/orchestrator')

try:
    from pulse import read_file_safe, select_and_update_rotation_item, select_cta_from_library, PHASE_MAPPING
except ImportError as e:
    print(f"🔴 Ошибка импорта pulse: {e}")
    sys.exit(1)

PROJECT = "/opt/zinaida/inbox/PROJECTS/Otnoshenya"
RAG_DB = "/opt/zinaida/memory/smm_rag.db"

def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def dump_prompt(phase_letter, pain_point):
    print(f"=== СБОРКА ПРОМПТА: ФАЗА {phase_letter} | БОЛЬ: {pain_point} ===\n")

    soul = read_file_safe(os.path.join(PROJECT, "agents/ZINAIDA_IDENTITY.md"), max_chars=15000)
    print(f"[СЛОЙ 0: ДНК] {len(soul)} символов")

    try:
        conn = get_conn(os.path.join(PROJECT, "phases.db"))
        cur = conn.cursor()
        cur.execute("SELECT * FROM phases WHERE phase_id LIKE ? || '_%' LIMIT 1", (phase_letter,))
        phase_data = cur.fetchone()
        conn.close()
        print(f"[СЛОЙ 1: ФАЗА] Запись из БД: {phase_data[0] if phase_data else 'НЕ НАЙДЕНО'}")
    except Exception as e:
        print(f"⚠️ Ошибка чтения phases.db: {e}")
        phase_data = None

    hook = select_and_update_rotation_item(os.path.join(PROJECT, "hooks/templates"), ".md", phase_letter, "hook_night_check_v1")
    stat = select_and_update_rotation_item(os.path.join(PROJECT, "stats/mechanics"), ".md", phase_letter, "stat_divorce")
    print(f"[СЛОЙ 3: ХУК] {hook[:100] if hook else 'ПУСТО'}...")
    print(f"[СЛОЙ 3: СТАТ] {stat[:100] if stat else 'ПУСТО'}...")

    story = read_file_safe(os.path.join(PROJECT, "micro_stories", "phase_A_trevoiga_01.md"), 1000)
    print(f"[СЛОЙ 3: ИСТОРИЯ] {story[:100] if story else 'ПУСТО'}...")

    rag_text = "НЕ НАЙДЕНО"
    try:
        rag_conn = get_conn(RAG_DB)
        rag_cur = rag_conn.cursor()
        try:
            rag_cur.execute("SELECT content FROM smm_knowledge_fts WHERE content MATCH ? AND project_name='Otnoshenya' LIMIT 1", (pain_point,))
        except sqlite3.OperationalError:
            rag_cur.execute("SELECT content FROM smm_knowledge_fts WHERE content LIKE ? AND project_name='Otnoshenya' LIMIT 1", (f"%{pain_point}%",))
        rag = rag_cur.fetchone()
        rag_conn.close()
        if rag:
            rag_text = rag[0][:150]
    except Exception as e:
        print(f"⚠️ Ошибка RAG-поиска: {e}")
    print(f"[СЛОЙ 4: RAG] {rag_text}...")

    cta, cta_file = select_cta_from_library(phase_letter, "tg")
    print(f"[СЛОЙ 5: CTA] Файл: {cta_file} | Текст: {cta[:50] if cta else 'ПУСТО'}...")

    print("\n=== ФИНАЛЬНЫЙ ПРОМПТ (ОТПРАВЛЯЕТСЯ В LLM) ===")
    prompt = f"""# ДНК ЗИНАИДЫ
{soul[:500]}... [ОБРЕЗАНО ДЛЯ ВЫВОДА]

[СЛОЙ 3: ХУК]
{hook}

[СЛОЙ 3: СТАТИСТИКА]
{stat}

[СЛОЙ 3: МИКРО-ИСТОРИЯ]
{story}

[СЛОЙ 5: CTA]
{cta}

Собери пост в JSON: {{"hook_options": ["вариант1", "вариант2"], "body": "текст", "cta": "{cta}"}}."""
    print(prompt)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 dump_prompt.py <ФАЗА> <БОЛЬ>")
        sys.exit(1)
    dump_prompt(sys.argv[1], sys.argv[2])
