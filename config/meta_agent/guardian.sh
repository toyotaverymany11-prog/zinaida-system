#!/bin/bash
ALERT_SCRIPT="/opt/zinaida/meta_agent/tg_alert.sh"
check_health() {
  local PORT=$1 NAME=$2
  local RESP=$(curl -s --max-time 5 "http://127.0.0.1:${PORT}/health" 2>/dev/null)
  if ! echo "$RESP" | grep -q '"ok"'; then
    bash "$ALERT_SCRIPT" "🚨 <b>GUARDIAN ALERT</b>\nService: ${NAME} (:${PORT})\nStatus: UNHEALTHY/UNREACHABLE\nResponse: ${RESP:-TIMEOUT}\nTime: $(date)"
  fi
}
check_health 8002 "Zinaida"
check_health 8003 "Grigoriy"
