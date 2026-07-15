#!/bin/bash
INBOX="/opt/zinaida/inbox"
LOG="/opt/zinaida/logs/smart_monitor.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Монитор перезапущен (без рекурсии)." >> "$LOG"
# ВАЖНО: Убрали -r. Теперь монитор видит только корень /inbox/ и игнорирует подпапки.
inotifywait -m -q -e close_write -e moved_to -e create --format '%w%f' "$INBOX" | while read FILE; do
  # Защита от временных файлов и случайного попадания подпапок
  if [[ -f "$FILE" && ! "$FILE" =~ \.(tmp|part|swp|lock)$ && "$FILE" != *"/processed/"* && "$FILE" != *"/errors/"* ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Обнаружен: $FILE" >> "$LOG"
    sleep 2
    /usr/bin/python3 /opt/zinaida/meta_agent/smart_learner.py "$FILE" >> "$LOG" 2>&1 &
  fi
done
