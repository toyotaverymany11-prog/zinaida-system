#!/bin/bash
set -e
FIX_FILE=$1
if [[ -z "$FIX_FILE" ]]; then
  echo "Использование: bash apply_fix.sh <имя_файла>"
  exit 1
fi

LOCK_FILE="/tmp/fix_apply.lock"
if [[ -f "$LOCK_FILE" ]]; then
  echo "Фикс уже применяется. Ждите."
  exit 1
fi
touch $LOCK_FILE
trap 'rm -f $LOCK_FILE' EXIT

BACKUP_TS=$(date +%s)
BACKUP_DIR="/opt/zinaida/backups/fix_${BACKUP_TS}"
mkdir -p "$BACKUP_DIR"

echo "Создание бэкапа..."
/bin/tar -czf "$BACKUP_DIR/critical_dirs.tar.gz" -C /opt/zinaida --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' meta_agent memory sandbox
/usr/bin/python3 /opt/zinaida/scripts/backup_db_safe.py "$BACKUP_DIR/unified_memory.db"

NEW_FILES_LOG="/tmp/fix_new_files_${BACKUP_TS}.txt"
/usr/bin/find /opt/zinaida/meta_agent /opt/zinaida/sandbox /opt/zinaida/memory -type f -newer $LOCK_FILE > $NEW_FILES_LOG 2>/dev/null || true

FIX_PATH="/opt/zinaida/inbox/research_pending/$FIX_FILE"
if [[ "$FIX_PATH" == *.py ]]; then
    env PYTHONPATH="/opt/zinaida/meta_agent:/opt/zinaida/sandbox" /usr/bin/python3 "$FIX_PATH"
elif [[ "$FIX_PATH" == *.sh ]]; then
    env PYTHONPATH="/opt/zinaida/meta_agent:/opt/zinaida/sandbox" /bin/bash "$FIX_PATH"
fi

echo "Рестарт роутера..."
/usr/bin/systemctl restart zinaida-router.service
sleep 3

if ! /usr/bin/curl -sf -m 5 http://127.0.0.1:8002/health > /dev/null; then
    echo "Тест health провален. Запуск отката..."
    /bin/bash /opt/zinaida/scripts/rollback_fix.sh "$BACKUP_DIR" "$NEW_FILES_LOG" "health_fail"
    exit 1
fi

echo "✅ Фикс $FIX_FILE успешно применён."
