#!/bin/bash
set -e
BACKUP_DIR=$1
NEW_FILES_LOG=$2
REASON=$3
echo "Запуск отката из $BACKUP_DIR. Причина: $REASON"

/usr/bin/systemctl stop zinaida-router.service
/usr/bin/systemctl stop grigoriy-router.service 2>/dev/null || true
sleep 2
rm -f /opt/zinaida/memory/unified_memory.db-wal /opt/zinaida/memory/unified_memory.db-shm
/usr/bin/python3 /opt/zinaida/scripts/restore_db_safe.py "$BACKUP_DIR/unified_memory.db"
/bin/tar -xzf "$BACKUP_DIR/critical_dirs.tar.gz" -C /opt/zinaida --overwrite
if [[ -f "$NEW_FILES_LOG" ]]; then
    while IFS= read -r f; do rm -f "$f"; done < "$NEW_FILES_LOG"
fi
/usr/bin/systemctl start zinaida-router.service
echo "Откат завершён."
