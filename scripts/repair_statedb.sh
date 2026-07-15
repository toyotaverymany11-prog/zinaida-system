#!/bin/bash
DB="/root/.hermes/state.db"
if ! sqlite3 "$DB" "SELECT 1;" 2>/dev/null; then
    echo "$(date) state.db повреждена, ремонтирую..." >> /var/log/hermes_repair.log
    cp "$DB" "${DB}.broken_$(date +%s)"
    sqlite3 "${DB}.broken_$(date +%s)" ".dump" 2>/dev/null | sqlite3 "${DB}.repaired"
    if sqlite3 "${DB}.repaired" "SELECT 1;" 2>/dev/null; then
        mv "${DB}.repaired" "$DB"
        echo "$(date) state.db восстановлена" >> /var/log/hermes_repair.log
    else
        rm -f "${DB}" "${DB}.repaired"
        echo "$(date) state.db пересоздана с нуля" >> /var/log/hermes_repair.log
    fi
fi
