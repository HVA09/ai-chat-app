# Off-site PostgreSQL backups

هذه الخطة تضيف نسخة احتياطية خارج Render باستخدام GitHub Actions + S3-compatible Object Storage.

## المطلوب قبل التفعيل

يجب إنشاء Bucket مخصص للنسخ الاحتياطية ثم إضافة هذه **GitHub Actions Secrets** في المستودع:

- `PRODUCTION_DATABASE_URL`
- `BACKUP_S3_BUCKET`
- `BACKUP_S3_ENDPOINT_URL`
- `BACKUP_S3_REGION`
- `BACKUP_S3_ACCESS_KEY_ID`
- `BACKUP_S3_SECRET_ACCESS_KEY`

لا تُحفظ هذه القيم في Git أو ملفات المشروع.

## السلوك

- تشغيل يدوي عبر GitHub Actions أو يوميًا.
- `pg_dump --format=custom` لعمل نسخة PostgreSQL.
- `pg_restore --list` للتحقق من سلامة ملف النسخة قبل الرفع.
- الرفع إلى:
  `s3://<bucket>/database/<timestamp>.dump`
- التحقق من وجود الملف عن طريق `head-object`.
- لا يتم طباعة الأسرار في سجل GitHub Actions.

## الحالة

التنفيذ البرمجي جاهز، لكن **Off-site backups لا تُعتبر مفعّلة** حتى يتم إنشاء Bucket وإضافة الأسرار وتشغيل Workflow بنجاح مرة واحدة على الأقل.

## ملاحظة

يمكن استخدام أي خدمة S3-compatible. لا يلزم إنشاء خدمة Render جديدة لهذا المسار.
