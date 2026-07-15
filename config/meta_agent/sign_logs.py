import os
import json
import hashlib
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

LOG_PATH = "/opt/zinaida/logs/routing_events.jsonl"
CHAIN_PATH = "/opt/zinaida/logs/log_chain.jsonl"

def main():
    if not os.path.exists(LOG_PATH):
        print("Лог маршрутизации не найден.")
        return

    prev_hash = "0" * 64
    if os.path.exists(CHAIN_PATH):
        try:
            with open(CHAIN_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    prev_hash = last_entry.get("current_hash", prev_hash)
        except Exception:
            pass

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return

        last_line = lines[-1].strip()
        if not last_line:
            return

        new_hash = hashlib.sha256(f"{prev_hash}:{last_line}".encode("utf-8")).hexdigest()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prev_hash": prev_hash,
            "current_hash": new_hash,
            "lines_count": len(lines)
        }
        with open(CHAIN_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"Цепочка обновлена. Хэш: {new_hash[:16]}...")
    except Exception as e:
        print(f"Ошибка подписи: {e}")

if __name__ == "__main__":
    main()
