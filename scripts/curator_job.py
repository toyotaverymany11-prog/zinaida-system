#!/usr/bin/env python3
import os, sys, json, sqlite3, fcntl, logging, warnings, time
from collections import Counter
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

LOCK_FILE = "/var/run/curator_job.lock"
DB_PATH = "/opt/zinaida/memory/smm_factory.db"
JSONL_PATH = "/opt/zinaida/yadro/ira_structured.jsonl"
CORE_PATH = "/opt/zinaida/inbox/PROJECTS/Otnoshenya/SMM_FACTORY_CORE.md"
MARKER = "# ДИНАМИЧЕСКИЕ ПРАВИЛА ХУКОВ"

def main():
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.warning("Curator already running. Exiting.")
        return

    try:
        logger.info("Starting weekly Curator pivot loop...")
        
        metrics = Counter()
        if os.path.exists(JSONL_PATH):
            with open(JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        if rec.get("metric") in ("save", "share"):
                            metrics[f"{rec.get('strategy','UNKNOWN')}_{rec.get('metric')}"] += 1
                    except json.JSONDecodeError:
                        continue
        logger.info(f"Metrics aggregated: {dict(metrics)}")

        common_errors = []
        if os.path.exists(DB_PATH):
            c = sqlite3.connect(DB_PATH, timeout=5)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=10000")
            rows = c.execute("SELECT details FROM trace_logs WHERE outcome='FAILED' ORDER BY timestamp_utc DESC LIMIT 50").fetchall()
            c.close()
            error_reasons = [r[0] for r in rows if r[0]]
            common_errors = Counter(error_reasons).most_common(3)
        logger.info(f"Top Verifier errors: {common_errors}")

        if not os.path.exists(CORE_PATH):
            logger.error("CORE.md not found. Abort.")
            return

        with open(CORE_PATH, "r", encoding="utf-8") as f:
            core_content = f.read()

        top_hooks_block = "\n".join([f"- {m}: {c} событий" for m, c in metrics.most_common(5)]) or "- Нет данных за период"
        errors_block = "\n".join([f"- {e[0]} ({e[1]} раз)" for e in common_errors]) or "- Ошибок не зафиксировано"
        
        dynamic_section = f"""{MARKER}
## ТОП МЕТРИК СТРАТЕГИЙ (Save/Share)
{top_hooks_block}

## ЧАСТЫЕ ОШИБКИ VERIFIER (ТРЕБУЮТ ПРАВКИ ПРОМПТОВ)
{errors_block}

## ДИРЕКТИВА PIVOT
- Приоритет генерации смещается в сторону стратегий с наибольшим Save Rate.
- Промпты агентов должны явно избегать паттернов, вызывающих ошибки Verifier.
- Обновлено: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

        if MARKER in core_content:
            parts = core_content.split(MARKER)
            new_core = parts[0] + dynamic_section
        else:
            new_core = core_content.rstrip() + "\n\n" + dynamic_section

        if len(new_core) < 2000:
            raise ValueError(f"New CORE.md too small ({len(new_core)}B). Rollback triggered.")

        tmp_core = CORE_PATH + ".tmp_curator"
        with open(tmp_core, "w", encoding="utf-8") as f:
            f.write(new_core)
        os.replace(tmp_core, CORE_PATH)
        os.chmod(CORE_PATH, 0o644)
        logger.info("CORE.md updated successfully. Pivot loop complete.")

    except Exception as e:
        logger.error(f"Curator failed: {e}")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

if __name__ == "__main__":
    main()
