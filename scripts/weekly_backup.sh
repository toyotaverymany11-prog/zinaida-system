#!/bin/bash
# Еженедельный бэкап контент-завода Зинаида
# Запуск: systemd-timer каждое воскресенье в 04:00
# Хранит 4 последних бэкапа (месяц)

set -euo pipefail

BACKUP_BASE="/opt/zinaida.Backup"
SOURCE="/opt/zinaida"
DATE=$(date +%Y%m%d)
TARGET="${BACKUP_BASE}.${DATE}"
LOG="/var/log/zinaida-backup.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Начинаю бэкап ${SOURCE} → ${TARGET}" >> "$LOG"

# Исключаем: кэш, пакеты, архивы, .bak, .tmp, sandbox
EXCLUDES=(
    "--exclude=*.bak" "--exclude=*.tmp"
    "--exclude=node_modules/" "--exclude=__pycache__/"
    "--exclude=.git/" "--exclude=.npm/"
    "--exclude=sandbox/" "--exclude=backups/"
    "--exclude=archive/"
    "--exclude=OneDrive/"
    "--exclude=memory/design_*.jpg" "--exclude=memory/design_*.png"
)

# Создаём бэкап через rsync (жёсткие ссылки — экономия места)
# --link-dest: если файл не менялся — создаёт hardlink, не копирует
LAST_BACKUP=$(ls -1d ${BACKUP_BASE}.* 2>/dev/null | sort | tail -1 || echo "")

if [ -n "$LAST_BACKUP" ]; then
    rsync -a --delete --link-dest="$LAST_BACKUP" "${EXCLUDES[@]}" \
        "$SOURCE/" "$TARGET/" >> "$LOG" 2>&1
else
    rsync -a --delete "${EXCLUDES[@]}" \
        "$SOURCE/" "$TARGET/" >> "$LOG" 2>&1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Бэкап готов: ${TARGET}" >> "$LOG"

# Удаляем бэкапы старше 4 недель (храним 4 штуки)
ls -1d ${BACKUP_BASE}.* 2>/dev/null | sort | head -n -4 | while read -r old; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Удаляю старый бэкап: ${old}" >> "$LOG"
    rm -rf "$old"
done

# Итоговый размер
TOTAL=$(du -sh "$TARGET" 2>/dev/null | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Размер: ${TOTAL}" >> "$LOG"
