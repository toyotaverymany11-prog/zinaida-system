import os
import sys
import json
import glob
import time
import subprocess
import sqlite3
import requests
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

LOGS_DIR = Path("/opt/zinaida/logs")
MEMORY_DIR = Path("/opt/zinaida/memory")
PROJECTS_DIR = MEMORY_DIR / "projects"
ROUTING_LOG = LOGS_DIR / "routing_events.jsonl"
ROUTER_URL = "http://127.0.0.1:8002/v1/chat/completions"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_recent_errors(hours=24):
    errors = []
    if not ROUTING_LOG.exists():
        return errors
    cutoff = time.time() - (hours * 3600)
    with open(ROUTING_LOG, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                evt = json.loads(line)
                if evt.get("status") == "error" or "429" in str(evt):
                    if evt.get("timestamp", 0) > cutoff:
                        errors.append(evt)
            except Exception:
                pass
    return errors[-50:]

def synthesize_light():
    log("Запуск лёгкого синтеза...")
    errors = get_recent_errors(24)
    if not errors:
        log("Ошибок не найдено. Пропуск.")
        return

    prompt = f"Проанализируй ошибки за 24 часа. Сделай краткие выводы и предложения по улучшению. Ошибки: {json.dumps(errors[:10], ensure_ascii=False)}"

    try:
        resp = requests.post(ROUTER_URL, json={
            "messages": [{"role": "user", "content": prompt}],
            "stream": False, "temperature": 0.2
        }, timeout=60)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']

        out_file = LOGS_DIR / f"synthesis_light_{datetime.now().strftime('%Y%m%d')}.md"
        out_file.write_text(f"# Лёгкий синтез {datetime.now().strftime('%Y-%m-%d')}\n\n{content}", encoding="utf-8")
        log(f"Сохранено в {out_file}")
    except Exception as e:
        log(f"Ошибка синтеза: {e}")

def synthesize_deep():
    log("Запуск глубокого синтеза...")
    light_files = sorted(glob.glob(str(LOGS_DIR / "synthesis_light_*.md")), reverse=True)[:7]
    combined = "\n---\n".join([Path(f).read_text(encoding="utf-8", errors="ignore") for f in light_files])

    if not combined.strip():
        log("Нет данных для глубокого синтеза.")
        return

    prompt = f"Проанализируй недельный опыт. Выяви долгосрочные паттерны. Сгенерируй новые навыки в формате JSON: {{\"skills\": [{{\"trigger\": \"...\", \"action\": \"...\", \"niche\": \"...\"}}]}}. Данные: {combined[:4000]}"

    try:
        resp = requests.post(ROUTER_URL, json={
            "messages": [{"role": "user", "content": prompt}],
            "stream": False, "temperature": 0.3, "routing_strategy": "analyze"
        }, timeout=120)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']

        out_file = LOGS_DIR / f"synthesis_deep_{datetime.now().strftime('%Y%m%d')}.md"
        out_file.write_text(f"# Глубокий синтез {datetime.now().strftime('%Y-%m-%d')}\n\n{content}", encoding="utf-8")
        log(f"Сохранено в {out_file}")

        draft_dir = PROJECTS_DIR / "global" / "skills" / "drafts"
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft_file = draft_dir / f"skill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        draft_file.write_text(content, encoding="utf-8")
        log(f"Черновик навыка: {draft_file}")

        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "Zinaida"
        env["GIT_AUTHOR_EMAIL"] = "zinaida@local"
        env["GIT_COMMITTER_NAME"] = "Zinaida"
        env["GIT_COMMITTER_EMAIL"] = "zinaida@local"
        subprocess.run(["git", "-C", str(MEMORY_DIR), "add", "."], check=False, env=env)
        subprocess.run(["git", "-C", str(MEMORY_DIR), "commit", "-m", "Night synthesis"], check=False, env=env)
    except Exception as e:
        log(f"Ошибка глубокого синтеза: {e}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "light"
    if mode == "deep":
        synthesize_deep()
    else:
        synthesize_light()
