#!/bin/bash
SKILL_PATH="$1"
if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH" ]; then exit 1; fi
SKILL_NAME=$(basename "$SKILL_PATH")
NICHE=$(echo "$SKILL_PATH" | grep -oP 'projects/\K[^/]+')
ACTIVE_DIR="/opt/zinaida/memory/projects/$NICHE/skills/active"
CMD="mv $SKILL_PATH $ACTIVE_DIR/$SKILL_NAME"

if [ -f /opt/zinaida/.env ]; then
    set -a; source /opt/zinaida/.env 2>/dev/null; set +a
fi
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    MSG="🧠 НОВЫЙ НАВЫК (DRAFT): $SKILL_NAME%0AНиша: $NICHE%0AУтверждение:%0A$CMD"
    curl -s -m 5 -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
         -d "chat_id=$TELEGRAM_CHAT_ID" \
         -d "text=$MSG" > /dev/null 2>&1 || true
fi
