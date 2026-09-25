# AI Platform Roadmap

هذه الوثيقة هي مرجع خارطة الطريق التنفيذية للمشروع. أي ميزة أو إصلاح جديد يجب أن ينسجم مع هذه المراحل، ولا ننتقل إلى مرحلة لاحقة قبل التحقق من متطلبات المرحلة الحالية.

## قواعد العمل

1. `main` هو مصدر الحقيقة الوحيد بين الأجهزة والفروع.
2. كل تغيير مهم يمر عبر PR مستقل مع CI وCodeQL عند توفرهما.
3. لا نعتبر المرحلة مكتملة بالوصف فقط؛ يجب التحقق من الاختبارات والتشغيل الفعلي.
4. قبل إضافة ميزة جديدة نراجع التكرار والتوافق مع المعمارية الحالية.
5. بعد كل مرحلة نسجل: ما تم، ما تم اختباره، وما بقي.
6. أي تغيير في البنية الإنتاجية يجب أن يحافظ على الأمن، قابلية التوسع، النسخ الاحتياطي، والمراقبة.
7. لا نعتبر النظام "Production-ready" بسبب نجاح CI وحده؛ يجب إجراء تحقق تشغيلي فعلي.

## المرحلة A — Production Foundation

الحالة: **قيد التنفيذ**

1. Render Health Check
2. Celery Worker
3. Celery Beat
4. ترقية PostgreSQL إلى إعداد إنتاجي مناسب
5. Redis بإعداد إنتاجي مناسب
6. Object Storage للملفات
7. Off-site backups
8. Domain + HTTPS
9. Production smoke tests وE2E

### الحالة التفصيلية الحالية

- Health Check: **endpoint متحقق، إعداد Render الداخلي غير مكتمل** — `/health` يعيد HTTP 200 مع `status=ok` و`database=ok`، لكن `healthCheckPath` الفعلي للخدمة ما زال فارغًا، ولا يوفّر اتصال Render الحالي أداة تعديل مباشرة لهذه الخاصية.
- Celery Worker: **يعمل مضمّنًا حاليًا** — سجلات Render تثبت استقبال وتنفيذ `run_due_scheduled_tasks` بنجاح دوريًا. توجد خدمة Worker مستقلة في `render.yaml` كهدف لاحق فقط.
- Celery Beat: **يعمل مضمّنًا حاليًا** — سجلات Render تثبت إرسال المهام المجدولة كل دقيقة تقريبًا. توجد خدمة Beat مستقلة في `render.yaml` كهدف لاحق فقط.
- PostgreSQL: **موجود فعليًا على Render بخطة Free** — `ai-chat-db`، PostgreSQL 18، الحالة `available`، وآخر migration `0065_object_storage`. المورد الحالي مؤقت وله انتهاء مجدول في **2026-10-10**.
- Redis: **موجود فعليًا على Render بخطة Free** — `ai-chat-redis`، الحالة `available`، و`persistenceMode=off`. التطبيق يستخدمه فعليًا، كما تثبت سجلات Celery.
- Object Storage: **مكتمل ومتحقق** — upload/read/delete ناجحة، وObject Storage Smoke في GitHub Actions نجح.
- Off-site backups: **مكتمل ومتحقق تشغيليًا** — أحدث Backup workflow `36167688637` نجح في `pg_dump`، التحقق من الأرشيف، الرفع إلى S3، و`head-object`.
- Domain + HTTPS: **غير مكتمل** — لا يوجد Custom Domain متحقق حاليًا.
- Production smoke tests/E2E: **Smoke مكتمل تشغيليًا** — workflow يعمل تلقائيًا على push إلى `main` بالإضافة إلى الجدولة والتشغيل اليدوي، وآخر تشغيلات Smoke ناجحة.
- Credential rotation: **مطلوب قبل الإغلاق الأمني** — إحدى محاولات Backup السابقة كشفت كلمة مرور DB في log بسبب اشتقاق `PGPASSWORD`. الـworkflow الحالي لم يعد يفعل ذلك، لكن يجب تدوير credential في Render وتحديث `PRODUCTION_DATABASE_URL`.

### تحقق Render الفعلي — 2026-09-25

- Workspace: `My Workspace` (`tea-dagsi5ou01pc73f2g470`).
- `ai-chat-backend`: Web Service، الخطة الحالية Free، `https://ai-chat-backend-ltxa.onrender.com`، وHealth Check Path الفعلي فارغ.
- `ai-chat-frontend`: Static Site، `https://ai-chat-frontend-v8ma.onrender.com`، والـpublic routes متحققة.
- `ai-chat-db`: PostgreSQL 18، Free، `available`، انتهاء مجدول 2026-10-10.
- `ai-chat-redis`: Redis 8.1.4، Free، `available`، persistence off.

### آخر تحقق تشغيلي — 2026-09-25

- Frontend live: `092a0525...`. `/`, `/pricing/`, `/terms/`, `/privacy/` أعادت HTTP 200، و`/pricing/` عرض Free وPro.
- CI على `092a0525...`: **نجح**، مع نجاح Backend pytest وFrontend وProduction Compose؛ CodeQL وPublish backend image نجحا أيضًا.
- Production Smoke على `0db359...` وما بعده: **نجح**، وأصبح جزءًا من push إلى `main` إضافة إلى الجدولة والتشغيل اليدوي.
- Production DB Backup النهائي: `36167688637` **نجح** بالكامل.
- Backup النهائي يستخدم S3 secrets الحالية، ويصل إلى PostgreSQL عبر External URL مع TLS؛ لم يعد يضع كلمة المرور المشتقة في `GITHUB_ENV` أو في بيئة job.
- تنبيه أمني مستمر: سجل محاولة Backup قديمة يحتوي credential مكشوفًا؛ يلزم تدوير credential من Render. تم وضع **قفل أمني** على Workflow في commit `39995b8...` بحيث لا ينفذ النسخ الاحتياطي المجدول/اليدوي حتى يتم تعيين `PRODUCTION_DB_CREDENTIAL_ROTATED=true` بعد تدوير credential فعليًا. Render يوصي بتدوير zero-downtime عبر إنشاء PostgreSQL credential جديد، تحديث الخدمات، إعادة النشر، ثم إزالة credential القديم. citeturn323554search0
- لم يتم إنشاء أو ترقية موارد Render مدفوعة.

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main`، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.
