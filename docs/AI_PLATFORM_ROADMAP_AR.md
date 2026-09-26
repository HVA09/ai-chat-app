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

الحالة: **قيد التنفيذ — PostgreSQL migrated; remaining foundation items are deferred/ongoing**

1. Render Health Check
2. Celery Worker
3. Celery Beat
4. PostgreSQL بإعداد إنتاجي مناسب
5. Redis بإعداد إنتاجي مناسب
6. Object Storage للملفات
7. Off-site backups
8. Domain + HTTPS
9. Production smoke tests وE2E

### الحالة التفصيلية الحالية

- Health Check: **مكتمل** — خدمة `ai-chat-backend` تستخدم الآن Health Check Path = `/health`، وآخر deploy بعد التغيير أصبح `live`. فحص الإنتاج يؤكد أن `/health` يعيد حالة سليمة وأن قاعدة البيانات متاحة.
- Celery Worker: **يعمل مضمّنًا حاليًا** — سجلات Render تثبت استقبال وتنفيذ `run_due_scheduled_tasks` بنجاح دوريًا. الخدمة المستقلة ما زالت هدفًا لاحقًا عند الحاجة إلى فصل الموارد.
- Celery Beat: **يعمل مضمّنًا حاليًا** — سجلات Render تثبت تشغيل الجدولة وإرسال المهام المجدولة دوريًا. الخدمة المستقلة ما زالت هدفًا لاحقًا.
- PostgreSQL: **تم ترحيله إلى Supabase بنجاح** — مشروع `ai-chat-prod-db` في `us-east-2` (Ohio)، PostgreSQL 17.6، وحالة المشروع `ACTIVE_HEALTHY`. تم استعادة النسخة من Render، ثم التحقق من تطابق جميع جداول `public` وعدد صفوفها (34 جدولًا). تم تحويل `DATABASE_URL` في Render إلى Supabase Session Pooler، وأكد Production Smoke نجاح التطبيق بعد التحويل. Render PostgreSQL القديم بقي موجودًا مؤقتًا كخطة رجوع حتى انتهاء المورد في **2026-10-10**؛ لا يُحذف الآن.
- Redis/Key Value: **متحقق تشغيليًا على Render Free** — الحالة `available`، و`persistenceMode=off`. سجلات الـbackend تؤكد اتصال Celery بـRedis وتشغيل المهام المجدولة بنجاح بصورة متكررة. لا يوجد إجراء مجاني لتمكين persistence؛ Render يوضح أن الاستمرارية غير متاحة على Free، لذلك يبقى Redis مخصصًا للكاش/الطوابير القابلة لإعادة البناء. فصل Worker عن الـbackend يبقى مؤجلًا لتجنب مورد إضافي مدفوع.
- Object Storage: **مكتمل ومتحقق** — اختبارات upload/read/delete نجحت.
- Off-site backups: **مكتمل ومتحقق تشغيليًا** — النسخ الاحتياطي الخارجي نجح قبل الترحيل، ثم تم تحديث Workflow ليدعم PostgreSQL الإنتاجي في Supabase، وتحديث `PRODUCTION_DATABASE_URL` إلى Supabase، وتشغيل النسخ الاحتياطي الجديد بنجاح.
- Credential rotation: **مكتمل** — تم إنشاء `production_db_2026`، تحديث خدمة الـbackend و`PRODUCTION_DATABASE_URL` في GitHub، حذف `ai_chat_db_6nnl_user`، وتحقق PostgreSQL من أن الحساب القديم لم يعد قابلًا لتسجيل الدخول. تم تعيين `PRODUCTION_DB_CREDENTIAL_ROTATED=true`.
- Domain + HTTPS: **HTTPS على نطاقات Render مكتمل** — خدمات Render تعمل عبر `onrender.com` مع HTTPS. **Custom Domain مؤجل** حاليًا لأن المستخدم لا يريد دفع تكلفة الآن ولا يوجد نطاق مخصص متحقق.
- Production smoke tests/E2E: **مكتمل تشغيليًا** — تشغيل يدوي نهائي نجح بعد آخر تغييرات. الاختبار يغطي `/health`، `/billing/plans`، تمرير `X-Request-ID`، الوصول إلى الواجهة الأمامية، والوصول إلى backend health.
- Observability: **مستمر** — `X-Request-ID` مرتبط بسياق logging، وProduction Smoke يتحقق من propagation.

### تحقق Render الفعلي — 2026-09-25

- `ai-chat-backend`: Web Service، الخطة Free، Health Check Path = `/health`، الحالة التشغيلية `live`.
- `ai-chat-frontend`: Static Site، الخطة Free، والواجهة العامة متاحة.
- `ai-chat-db`: PostgreSQL 18، Free، `available`، انتهاء مجدول 2026-10-10.
- `ai-chat-redis`: Free، `available`، persistence off.
- لم يتم إنشاء أو ترقية موارد Render مدفوعة.

### آخر تحقق تشغيلي — 2026-09-25

- Production DB Backup بعد تدوير credential: **نجح** بالكامل، بما في ذلك `pg_dump`، `pg_restore --list`، الرفع، و`head-object`.
- Production Smoke النهائي بعد آخر نشر: **نجح**.
- PostgreSQL connections بعد التدوير كانت باسم `production_db_2026`، ولم توجد اتصالات فعالة باسم الحساب القديم.
- الحساب القديم `ai_chat_db_6nnl_user` لم يعد قابلًا لتسجيل الدخول.
- Health Check الجديد على Render أصبح فعالًا وأحدث deploy أصبح `live`.

### الأولوية التالية

**استقرار ما بعد الترحيل ثم إكمال عناصر Stage A المتبقية بدون إنشاء مورد مدفوع.**

PostgreSQL أصبح محفوظًا على Supabase، والنسخ الاحتياطي الخارجي يعمل. يبقى Render PostgreSQL القديم كخطة رجوع مؤقتة حتى 2026-10-10. بعد التأكد من الاستقرار، نتابع العناصر المؤجلة مثل تحسين Redis persistence، فصل Celery عند الحاجة، وCustom Domain عند توفر نطاق وميزانية.

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main)، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.


### تحقق Redis وCelery — مكتمل ومتحقق — 2026-09-26

- Redis/Key Value: اتصالات نشطة مؤكدة، وCelery متصل بـRedis عبر الشبكة الداخلية.
- Celery Worker وBeat: تشغيل فعلي مؤكد، مع نجاح متكرر للمهمة `run_due_scheduled_tasks` دون أخطاء في السجلات.
- قرار التكلفة: لا نرفع Redis إلى خطة مدفوعة ولا ننشئ Background Worker مستقلًا في هذه المرحلة، لأن الهدف الحالي هو البقاء بدون دفع.

### ترحيل PostgreSQL — مكتمل ومتحقق — 2026-09-26

- تم إنشاء Supabase مجانًا بدون مورد مدفوع.
- تم استعادة نسخة PostgreSQL إلى Supabase والتحقق من تطابق **34/34 جدولًا** في `public` مع قاعدة Render.
- تم تحويل `DATABASE_URL` للإنتاج إلى Supabase Session Pooler.
- Production Smoke بعد التحويل: **نجح**.
- Production DB Backup بعد التحويل إلى Supabase: **نجح**.
- تم تفعيل RLS على **34/34 جدولًا** في `public` كحماية لطبقة Supabase Data API، بدون إضافة سياسات تخمينية قد تتعارض مع نموذج صلاحيات التطبيق. التطبيق يستخدم اتصال PostgreSQL مباشرًا من الـbackend.
- بقي تحذير غير حرج: امتداد `vector` موجود في schema `public` بسبب متطلبات استعادة النسخة الحالية؛ لا يتم نقله الآن حتى لا نخاطر بوظائف embeddings. يُراجع لاحقًا عند توفر نافذة آمنة للتعديل.
- Render PostgreSQL القديم لا يزال احتياطي رجوع مؤقتًا حتى 2026-10-10.
