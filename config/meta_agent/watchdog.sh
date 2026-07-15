#!/bin/bash
# Zinaida Router Watchdog v2.0
LOG="/opt/zinaida/logs/watchdog.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Проверяем роутер
if ! curl -sf http://localhost:8002/health > /dev/null 2>&1; then
    echo "$TIMESTAMP [WATCHDOG] Router DOWN — restarting..." >> "$LOG"
    systemctl restart zinaida-router
    sleep 3
    if curl -sf http://localhost:8002/health > /dev/null 2>&1; then
        echo "$TIMESTAMP [WATCHDOG] Router RECOVERED after restart" >> "$LOG"
    else
        echo "$TIMESTAMP [WATCHDOG] Router STILL DOWN after restart!" >> "$LOG"
    fi
fi

# Проверяем Hermes Web UI
if ! systemctl is-active --quiet hermes-web-ui; then
    echo "$TIMESTAMP [WATCHDOG] Hermes Web UI DOWN — restarting..." >> "$LOG"
    systemctl restart hermes-web-ui
fi

# Проверяем Hermes Gateway
if ! systemctl is-active --quiet hermes-gateway; then
    echo "$TIMESTAMP [WATCHDOG] Hermes Gateway DOWN — restarting..." >> "$LOG"
    systemctl restart hermes-gateway
fi
