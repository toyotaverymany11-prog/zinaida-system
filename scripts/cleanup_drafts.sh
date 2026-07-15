#!/bin/bash
# Очистка устаревших черновиков (DRAFT_COPY, RESEARCH_FINDING) старше 24 часов
DB="/opt/zinaida/memory/smm_factory.db"
LOCK="/var/run/cleanup_drafts.lock"
LOG="/opt/zinaida/logs/cleanup_drafts.log"

exec 200>"$LOCK"
flock -n 200 || { echo "$(date): Already running" >> "$LOG"; exit 1; }

if [ -f "$DB" ]; then
    sqlite3 "$DB" <<SQL
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=10000;
DELETE FROM shared_memory_insights 
WHERE insight_type IN ('DRAFT_COPY', 'RESEARCH_FINDING') 
AND timestamp_utc < datetime('now', '-24 hours');
SQL
    echo "$(date): Cleanup done. Rows affected: $?" >> "$LOG"
else
    echo "$(date): DB not found" >> "$LOG"
fi

flock -u 200
