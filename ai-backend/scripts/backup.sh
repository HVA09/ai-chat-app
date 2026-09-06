#!/bin/sh
# نسخة احتياطية لقاعدة البيانات — تحذف تلقائيًا أي نسخة أقدم من 7 أيام
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/backup_${TIMESTAMP}.sql.gz"

mkdir -p /backups
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"
echo "تم حفظ نسخة احتياطية: $BACKUP_FILE"

find /backups -name "backup_*.sql.gz" -mtime +7 -delete
