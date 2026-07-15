#!/bin/bash
PID_FILE="/var/run/smm_watchdog.pid"
LOG_FILE="/opt/zinaida/ERROR_LOG/watchdog.log"
SMM_DB="/opt/zinaida/memory/smm_factory.db"

exec 200>"$PID_FILE"
if ! flock -n 200; then
    echo "[$(date)] Watchdog уже запущен. Пропуск." >> "$LOG_FILE"
    exit 0
fi
echo $$ >&200

PORTS_OK=true
for port in 8001 8002; do
    if ! curl -sI --max-time 3 "http://127.0.0.1:$port/" >/dev/null 2>&1; then
        echo "[$(date)] АЛЕРТ: Порт $port недоступен." >> "$LOG_FILE"
        sqlite3 "$SMM_DB" "INSERT INTO shared_memory_insights (record_id, agent_name, insight_type, content, timestamp_utc) VALUES ('alert_port_${port}_$(date +%s)', 'Watchdog', 'ALERT', 'Port $port unavailable', datetime('now'))"
        PORTS_OK=false
    fi
done

FAILURES=$(sqlite3 "$SMM_DB" "SELECT COUNT(*) FROM trace_logs WHERE outcome IN ('FAILURE', 'TIMEOUT') AND timestamp_utc > datetime('now', '-1 hour')")
if [ "$FAILURES" -gt 0 ]; then
    echo "[$(date)] АЛЕРТ: $FAILURES сбоев за последний час." >> "$LOG_FILE"
    sqlite3 "$SMM_DB" "INSERT INTO shared_memory_insights (record_id, agent_name, insight_type, content, timestamp_utc) VALUES ('alert_failures_$(date +%s)', 'Watchdog', 'ALERT', '$FAILURES failures in last hour', datetime('now'))"
fi

sqlite3 "$SMM_DB" "UPDATE system_metrics SET metric_value=datetime('now'), timestamp_utc=datetime('now') WHERE metric_name='watchdog_last_run'"

echo "[$(date)] Watchdog завершён. Порты: $PORTS_OK. Сбои: $FAILURES." >> "$LOG_FILE"
