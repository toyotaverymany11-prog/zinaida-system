import sqlite3
import sys

BACKUP_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/unified_memory_backup.db"
DB_PATH = "/opt/zinaida/memory/unified_memory.db"

try:
    src = sqlite3.connect(BACKUP_PATH)
    dst = sqlite3.connect(DB_PATH, timeout=5)
    src.backup(dst)
    dst.close()
    src.close()
    print("Восстановление БД успешно выполнено.")
except Exception as e:
    print(f"Ошибка восстановления БД: {e}", file=sys.stderr)
    sys.exit(1)
