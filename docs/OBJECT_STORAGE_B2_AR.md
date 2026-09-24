# Object Storage — إعداد Backblaze B2

المشروع يدعم S3-compatible Object Storage عبر boto3. Backblaze B2 يوفّر S3-Compatible API، ويستخدم AWS Signature Version 4. عنوان الـ endpoint يكون بالشكل:
`https://s3.<region>.backblazeb2.com`

المصدر: Backblaze S3-Compatible API documentation.

## التكلفة

صفحة أسعار Backblaze الحالية تذكر أن أول 10 GB من التخزين مجانية، مع egress مجاني حتى 3× متوسط التخزين الشهري وفق السياسة المنشورة. التخزين بعد الحد المجاني يخضع لتسعير B2. راجع صفحة الأسعار قبل الاعتماد على استخدام أكبر.

## إعداد B2

1. أنشئ حساب Backblaze وفعّل B2.
2. أنشئ Bucket خاصًا بالمشروع.
3. من App Keys أنشئ Application Key مخصصًا لهذا الاستخدام. الـ master application key غير مدعوم مع S3-Compatible API.
4. احتفظ بالقيم التالية:
   - Bucket name
   - S3 Endpoint URL
   - Region
   - Application Key ID
   - Application Key

مثال endpoint:
`https://s3.us-west-004.backblazeb2.com`

## متغيرات Render

بعد إنشاء الـ Bucket، ضع القيم في خدمة `ai-chat-backend`:

`S3_BUCKET`
`S3_ENDPOINT_URL`
`S3_REGION`
`S3_ACCESS_KEY_ID`
`S3_SECRET_ACCESS_KEY`

لا تضع الـ Application Key أو Secret في Git.

## اختبار Object Storage

تمت إضافة:
`.github/workflows/object-storage-smoke.yml`

لكن الـ workflow محمي بمتغير Repository:
`OBJECT_STORAGE_SMOKE_ENABLED=true`

وSecrets المطلوبة:

`S3_BUCKET`
`S3_ENDPOINT_URL`
`S3_REGION`
`S3_ACCESS_KEY_ID`
`S3_SECRET_ACCESS_KEY`

الاختبار يقوم برفع ملف صغير، التحقق منه، تنزيله ومقارنته، ثم حذفه.

## الحالة

هذا التغيير يجهز التحقق التشغيلي، لكنه لا ينشئ حساب Backblaze أو Bucket أو مفاتيح الوصول، لذلك لا نعتبر Object Storage مفعّلًا إنتاجيًا قبل تشغيل الاختبار بنجاح مرة واحدة على الأقل.

## ملاحظة تشغيلية

طبقة التخزين الحالية تستخدم Object Storage فقط عندما تكون قيم S3 الخمس موجودة. عند غيابها يبقى التخزين المحلي كـ fallback.
