#!/bin/bash
PROC_DIR="/opt/zinaida/inbox/processing"
ERR_DIR="/opt/zinaida/inbox/errors"
LOG="/opt/zinaida/logs/watchdog.log"
mkdir -p "$ERR_DIR"
find "$PROC_DIR" -type f -mmin +10 2>/dev/null | while read -r file; do
    fname=$(basename "$file")
    mv "$file" "$ERR_DIR/" 2>/dev/null || true
    echo "$(date '+%Y-%m-%d %H:%M:%S') WATCHDOG: Moved stuck file $fname to errors" >> "$LOG"
    if [ -x /opt/zinaida/scripts/tg_alert.sh ]; then
        /opt/zinaida/scripts/tg_alert.sh "WATCHDOG: File $fname stuck >10min. Moved to errors." 2>/dev/null || true
    fi
done
