# Object Storage — إعداد مجاني باستخدام Backblaze B2

المشروع يدعم S3-compatible Object Storage عبر boto3. Backblaze B2 يوفّر S3-Compatible API، ويمكن استخدامه دون تغيير طبقة التخزين الحالية تقريبًا. توثيق Backblaze الرسمي يوضح أن endpoint يكون بالشكل `https://s3.<region>.backblazeb2.com` وأن مصادقة S3 تستخدم Signature V4. citeturn586620search0turn586620search1

## التكلفة

بحسب صفحة الأسعار الحالية من Backblaze، أول 10 GB من التخزين مجانية في B2، مع سياسة egress مجانية حتى 3× متوسط التخزين الشهري ضمن الحد المعلن. الحساب المجاني ليس مورد Render ولا ينشئ خدمة مدفوعة على Render. citeturn832840search0turn832840search4

## إعداد B2

1. أنشئ حساب Backblaze وفعّل B2.
2. أنشئ Bucket خاصًا بالمشروع، ويفضّل تسميته باسم فريد مثل `ai-chat-app-files-<suffix>`.
3. من App Keys أنشئ Application Key مخصصًا لهذا الاستخدام. Backblaze لا يسمح باستخدام الـ master application key مع S3-Compatible API؛ يجب إنشاء Application Key يدوي. citeturn586620search1turn586620search4
4. احتفظ بـ:
   - Bucket name
   - S3 Endpoint URL
   - Region
   - Application Key ID
   - Application Key

صيغة endpoint الرسمية تكون مثل:
`https://s3.us-west-004.backblazeb2.com` citeturn586620search0

## متغيرات Render

بعد إنشاء الـ Bucket، ضع القيم في خدمة `ai-chat-backend`:

`S3_BUCKET`
`S3_ENDPOINT_URL`
`S3_REGION`
`S3_ACCESS_KEY_ID`
`S3_SECRET_ACCESS_KEY`

لا تضع الـ Application Key أو الـ Secret في Git.

## اختبار آمن

تمت إضافة GitHub Actions workflow:
`.github/workflows/object-storage-smoke.yml`

لكنّه محمي بمتغير Repository:
`OBJECT_STORAGE_SMOKE_ENABLED=true`

ولا يعمل قبل ضبط المتغير والأسرار المطلوبة. يقوم الاختبار بإنشاء ملف صغير، رفعه، فحصه، تنزيله مرة أخرى، ثم حذفه.

## ملاحظة تشغيلية

طبقة التخزين الحالية تستخدم Object Storage فقط عندما تكون جميع قيم S3 الخمس موجودة. عند غيابها يبقى التخزين المحلي هو fallback. هذا يسمح بمرحلة انتقالية بدون كسر التشغيل الحالي.

## بعد التفعيل

يجب تشغيل Object Storage smoke workflow بنجاح مرة واحدة على الأقل، ثم يمكن اعتبار بند Object Storage في Phase A متحققًا تشغيليًا.
