#!/bin/bash
# Watchdog v3 — ТОЛЬКО алерты. Systemd сам рестартит сервисы (Restart=on-failure)
# Причина вылетов 16.07: watchdog делал systemctl restart → валил web-ui + gateway + router
LOG="/opt/zinaida/logs/watchdog.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

check_and_alert() {
    local svc=$1
    if ! systemctl is-active --quiet "$svc"; then
        echo "$TIMESTAMP [WATCHDOG] ❌ $svc DOWN — systemd должен поднять" >> "$LOG"
    fi
}

check_and_alert "hermes-web-ui.service"
check_and_alert "hermes-gateway.service"
check_and_alert "hermes4-router.service"
check_and_alert "zinaida-router.service"
check_and_alert "zina2-router-8005.service"
