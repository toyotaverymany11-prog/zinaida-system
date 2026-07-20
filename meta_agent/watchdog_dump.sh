#!/bin/bash
HASH_FILE="/opt/zinaida/meta_agent/.last_alert_hash"
ERROR_DIR="/opt/zinaida/inbox/errors"
TG_TOKEN=$(grep '^TG_BOT_TOKEN=' /opt/zinaida/.env | head -1 | cut -d'=' -f2-)
TG_CHAT=$(grep '^TG_CHAT_ID=' /opt/zinaida/.env | head -1 | cut -d'=' -f2-)

DUMP=""
curl -s -m 3 http://127.0.0.1:8002/health | grep -q '"status":"ok"' || DUMP+="zinaida_down "
curl -s -m 3 http://127.0.0.1:8003/health | grep -q '"status":"ok"' || DUMP+="grigoriy_down "

SS_OUT=$(ss -tlnp | grep -E '8002|8003' || echo "ports_missing")
if [[ "$SS_OUT" == *"ports_missing"* ]]; then DUMP+="ports_missing "; fi

JNL_OUT=$(journalctl -u zinaida-router.service -u grigoriy-router.service --since "5 min ago" --no-pager | grep -iE "error|critical|traceback" | tail -5)

if [ -n "$DUMP" ]; then
    NORM=$(echo "$DUMP $SS_OUT $JNL_OUT" | sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.,]+//g; s/[A-Z][a-z]{2} +[0-9]{1,2} +[0-9:]+//g; s/\b(pid|PID)[=: ]+[0-9]+\b//g; s/\btrace_id[=: ]+["a-zA-Z0-9]+\b//g; s/\bline [0-9]+\b//g')
    HASH=$(echo "$NORM" | sha256sum | cut -d' ' -f1)
    LAST_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "none")
    LAST_TIME=$(stat -c %Y "$HASH_FILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_TIME))
    
    if [ "$HASH" != "$LAST_HASH" ] || [ "$DIFF" -gt 3600 ]; then
        echo "$HASH" > "$HASH_FILE"
        echo "$(date) DUMP: $DUMP | SS: $SS_OUT | JNL: $JNL_OUT" > "$ERROR_DIR/error_${NOW}.txt"
        curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" -d "chat_id=${TG_CHAT}&text=ALERT: $DUMP" >/dev/null 2>&1
    fi
fi
