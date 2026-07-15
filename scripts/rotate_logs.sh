#!/bin/bash
LOG_FILE="/opt/zinaida/logs/provider_usage.json"
if [ -f "$LOG_FILE" ]; then
    python3 -c "
import json
try:
    with open('$LOG_FILE', 'r') as f: data = json.load(f)
    if len(data) > 100:
        data = data[-100:]
        with open('$LOG_FILE', 'w') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        print('✅ Лог обрезан до 100 записей')
    else: print('✅ Лог в норме (<=100 записей)')
except Exception as e: print(f'❌ Ошибка: {e}')
"
else echo "⚠️ Файл $LOG_FILE не найден"; fi
