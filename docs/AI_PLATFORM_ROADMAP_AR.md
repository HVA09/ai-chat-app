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
- PostgreSQL: **يعمل فعليًا على Render بخطة Free** — `ai-chat-db`، PostgreSQL 18، الحالة `available`. المستخدم الحالي للتطبيق هو `production_db_2026`. المورد الحالي مؤقت وتنتهي صلاحيته في **2026-10-10**؛ يلزم تنفيذ خطة حفظ/ترحيل قبل هذا التاريخ إذا أردنا الاستمرار بدون خطة مدفوعة.
- Redis: **يعمل فعليًا على Render بخطة Free** — الحالة `available`، و`persistenceMode=off`. يستخدمه التطبيق وCelery فعليًا. ما زال الضبط الحالي مناسبًا للتشغيل المجاني وليس استمرارية بيانات قوية.
- Object Storage: **مكتمل ومتحقق** — اختبارات upload/read/delete نجحت.
- Off-site backups: **مكتمل ومتحقق تشغيليًا** — workflow النهائي للنسخ الاحتياطي نجح في dump، التحقق من الأرشيف، الرفع إلى Object Storage، والتحقق من النسخة البعيدة.
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

**حفظ استمرارية PostgreSQL قبل 2026-10-10 بدون إنشاء مورد مدفوع.**

الهدف هو تجهيز مسار ترحيل مجاني/منخفض التكلفة باستخدام النسخة الاحتياطية المتحقق منها، مع الحفاظ على عدم فقد البيانات. بعد ذلك يمكن إغلاق بقية عناصر Stage A أو تأجيل Custom Domain إلى حين توفر نطاق مخصص.

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main)، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.
