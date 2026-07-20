#!/bin/bash
ENV_FILE="/opt/zinaida/meta_agent/.env"
TG_TOKEN=$(grep -iE 'TG_BOT_TOKEN|TELEGRAM_BOT_TOKEN' "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
TG_CHAT=$(grep -iE 'TG_CHAT_ID|TELEGRAM_CHAT_ID' "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
if [ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT" ]; then
  echo "$(date): TG credentials missing in .env" >> /opt/zinaida/logs/guardian_alerts.log
  exit 1
fi
LAST_ALERT_FILE="/tmp/last_tg_alert.txt"
NOW=$(date +%s)
if [ -f "$LAST_ALERT_FILE" ]; then
  LAST=$(cat "$LAST_ALERT_FILE")
  DIFF=$((NOW - LAST))
  if [ "$DIFF" -lt 600 ]; then exit 0; fi
fi
MSG="${1:-🚨 Zinaida Guardian: Service health check failed.}"
RESP=$(curl -s --max-time 10 -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT}" -d "text=${MSG}" -d "parse_mode=HTML" 2>/dev/null)
if echo "$RESP" | grep -q '"ok":true'; then
  echo "$NOW" > "$LAST_ALERT_FILE"
else
  echo "$(date): TG API failed: $RESP" >> /opt/zinaida/logs/guardian_alerts.log
fi
