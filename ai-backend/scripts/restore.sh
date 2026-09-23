#!/bin/sh
# استرجاع نسخة احتياطية — الاستخدام:
#   docker compose exec -e CONFIRM_RESTORE=YES -T db sh /scripts/restore.sh /backups/backup_XXXXXXXX_XXXXXX.sql.gz
set -e

if [ -z "${1:-}" ]; then
  echo "الاستخدام: restore.sh <ملف_النسخة.sql.gz>"
  exit 1
fi

if [ "${CONFIRM_RESTORE:-}" != "YES" ]; then
  echo "رفض الاسترجاع: العملية تستبدل بيانات قاعدة البيانات الحالية بالكامل."
  echo "للتأكيد الصريح استخدم CONFIRM_RESTORE=YES."
  exit 1
fi

test -f "$1"

echo "جارٍ استرجاع النسخة الاحتياطية: $1"
gunzip -c "$1" | psql "$DATABASE_URL"
echo "تم استرجاع النسخة الاحتياطية بنجاح"
