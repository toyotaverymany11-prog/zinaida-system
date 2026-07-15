#!/bin/bash
HEALTH=$(curl -s --connect-timeout 5 localhost:8002/health 2>/dev/null)
if [ -z "$HEALTH" ]; then
    echo "$(date) ALERT: роутер не отвечает! Перезапуск..." >> /var/log/router_monitor.log
    systemctl restart zinaida-router.service
    sleep 5
    HEALTH2=$(curl -s --connect-timeout 5 localhost:8002/health 2>/dev/null)
    if [ -z "$HEALTH2" ]; then
        echo "$(date) КРИТИЧНО: роутер не поднялся!" >> /var/log/router_monitor.log
    else
        echo "$(date) Роутер восстановлен" >> /var/log/router_monitor.log
    fi
fi
