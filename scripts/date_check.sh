#!/bin/bash
# date_check.sh — проверка даты перед любым действием с файлами
# Выполнять ПЕРЕД любым сохранением, генерацией, созданием папок
# Запуск: bash /opt/zinaida/scripts/date_check.sh

echo "=== ТЕКУЩАЯ ДАТА (единственный источник правды) ==="
echo "Системная дата: $(date '+%Y-%m-%d %H:%M %A')"
echo "Для папок: $(date '+%Y-%m-%d')"
echo "Для подписей: $(date '+%d.%m.%Y')"

# Проверка что дата валидна
DATE_NUM=$(date '+%Y%m%d')
if [ "$DATE_NUM" -gt "20260101" ] && [ "$DATE_NUM" -lt "20270101" ]; then
    echo "✅ Дата валидна (2026 год)"
else
    echo "❌ ОШИБКА: дата вне допустимого диапазона!"
    exit 1
fi

export TODAY=$(date '+%Y-%m-%d')
echo "TODAY=$TODAY"
