#!/bin/sh
# استرجاع نسخة احتياطية — الاستخدام:
#   docker compose exec -T db sh /scripts/restore.sh /backups/backup_XXXXXXXX_XXXXXX.sql.gz
set -e

if [ -z "$1" ]; then
  echo "الاستخدام: restore.sh <ملف_النسخة.sql.gz>"
  exit 1
fi

echo "تحذير: هذا سيستبدل بيانات قاعدة البيانات الحالية بالكامل. اضغط Enter للمتابعة أو Ctrl+C للإلغاء."
read _

gunzip -c "$1" | psql "$DATABASE_URL"
echo "تم استرجاع النسخة الاحتياطية بنجاح"
