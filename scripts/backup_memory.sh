#!/usr/bin/env bash
# Автоматический бэкап памяти Зинаиды
# Запуск: ежедневно через cron
set -e

DATE=$(date '+%Y-%m-%d')
BACKUP_DIR="/opt/zinaida/backups/memory"
mkdir -p "$BACKUP_DIR"

ARCHIVE="$BACKUP_DIR/memory_backup_$DATE.tar.gz"

# Что бэкапим
tar -czf "$ARCHIVE" \
  /root/.hermes/memories/MEMORY.md \
  /root/.hermes/memories/USER.md \
  /root/.hermes/memory_store.db \
  /root/.hermes/config.yaml \
  /root/.hermes/SOUL.md \
  /root/.hermes/AGENTS.md \
  /opt/zinaida/meta_agent/.env \
  /opt/zinaida/shared_memory/updates_log.md \
  /opt/zinaida/projects/Otnoshenya/planner/ \
  2>/dev/null

echo "✅ Бэкап: $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

# Удаляем старше 7 дней
find "$BACKUP_DIR" -name "memory_backup_*.tar.gz" -mtime +7 -delete
echo "🗑 Старые бэкапы удалены"
