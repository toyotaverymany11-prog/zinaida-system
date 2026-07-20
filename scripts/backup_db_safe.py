import sqlite3
import sys

DB_PATH = "/opt/zinaida/memory/unified_memory.db"
BACKUP_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/unified_memory_backup.db"

try:
    src = sqlite3.connect(DB_PATH, timeout=5)
    dst = sqlite3.connect(BACKUP_PATH)
    src.backup(dst)
    dst.close()
    src.close()
    print("Бэкап БД успешно создан.")
except Exception as e:
    print(f"Ошибка бэкапа БД: {e}", file=sys.stderr)
    sys.exit(1)
