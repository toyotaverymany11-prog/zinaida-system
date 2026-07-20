#!/bin/bash
# АВТО-БЭКАП КОНФИГОВ HERMES — вызывать ПЕРЕД любым изменением config.yaml
# Использование: bash config_backup.sh [причина]
# Создаёт датированный бэкап всех профилей с комментарием

BACKUP_DIR="/opt/zinaida/backups/configs"
REASON="${1:-manual}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
PROFILES_DIR="/root/.hermes/profiles"

mkdir -p "$BACKUP_DIR"

echo "=== CONFIG BACKUP $TIMESTAMP ==="
echo "Причина: $REASON"
echo ""

# Бэкап всех профилей
for profile_dir in "$PROFILES_DIR"/*/; do
    profile_name=$(basename "$profile_dir")
    src="$profile_dir/config.yaml"
    if [ -f "$src" ]; then
        dst="$BACKUP_DIR/${profile_name}_${TIMESTAMP}.yaml"
        cp "$src" "$dst"
        echo "✅ $profile_name → $(basename $dst)"
    fi
done

# Бэкап основного конфига
MAIN_CONFIG="/root/.hermes/config.yaml"
if [ -f "$MAIN_CONFIG" ]; then
    dst="$BACKUP_DIR/main_${TIMESTAMP}.yaml"
    cp "$MAIN_CONFIG" "$dst"
    echo "✅ main → $(basename $dst)"
fi

# Лог
echo "$TIMESTAMP | $REASON | $(whoami)" >> "$BACKUP_DIR/backup.log"

# Оставляем только последние 20 бэкапов
ls -t "$BACKUP_DIR"/*_*.yaml 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null

echo ""
echo "Готово. Бэкапы в $BACKUP_DIR"
