#!/bin/bash
# Healthcheck веб-окна v3 — ТОЛЬКО мониторинг, НИКАКИХ restart
# 16.07: убраны все systemctl restart — они валили окно
# systemd сам перезапустит сервисы (Restart=on-failure)
LOG_TAG="webui-healthcheck"
URL="https://zinadchdp.duckdns.org"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" --max-time 10 2>/dev/null)

if [[ "$HTTP_CODE" != "200" ]]; then
    logger -t "$LOG_TAG" "⚠️ Web UI ответил $HTTP_CODE (ожидался 200)"
    logger -t "$LOG_TAG" "web-ui: $(systemctl is-active hermes-web-ui), caddy: $(systemctl is-active caddy), gw: $(systemctl is-active hermes-gateway)"
else
    logger -t "$LOG_TAG" "✅ OK"
fi
