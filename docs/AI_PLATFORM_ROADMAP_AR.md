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
- Production smoke tests/E2E: **مكتمل تشغيليًا وموسع** — التشغيل يغطي `/health`، `/ready`، `/billing/plans`، تمرير `X-Request-ID`، والوصول إلى الواجهة الأمامية. تم إضافة retries لمعالجة cold starts على Render Free.
- Observability: **قيد الاستكمال** — `X-Request-ID` مرتبط بسياق logging، وProduction Smoke يتحقق من propagation، وتمت إضافة readiness عميقة تعتمد على DB + Redis.

### تحقق Render الفعلي — 2026-09-26

- `ai-chat-backend`: Web Service، الخطة Free، Health Check Path = `/health`.
- آخر deploy للcommit `e14cf2e4b517282c69ae70f8eefb221e764ba831` أصبح **live**.
- Production Smoke للcommit الجديد: **نجح**.
- لم يتم إنشاء أو ترقية موارد Render مدفوعة.

### آخر تحقق تشغيلي — 2026-09-26

- Production DB Backup بعد تدوير credential: **نجح** بالكامل.
- Production Smoke السابق بعد التغييرات الأساسية: **نجح**.
- Health Check الجديد على Render أصبح فعالًا.
- readiness endpoint موجود ومربوط بفحص قاعدة البيانات وRedis.
- التحقق المباشر من endpoint من بيئة التنفيذ المحلية تعذر بسبب فشل DNS، لذلك لا نسجل نتيجة HTTP مباشرة من هذه البيئة كدليل مستقل.

### الأولوية التالية

**إكمال Production Hardening (Stage B) بدون إنشاء مورد مدفوع، ثم الانتقال إلى ميزات المنتج بعد إغلاق بنود B الحرجة.**

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main`، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.

### تحقق Redis وCelery — مكتمل ومتحقق — 2026-09-26

- Redis/Key Value: اتصالات نشطة مؤكدة، وCelery متصل بـRedis عبر الشبكة الداخلية.
- Celery Worker وBeat: تشغيل فعلي مؤكد، مع نجاح متكرر للمهمة `run_due_scheduled_tasks` دون أخطاء في السجلات.
- قرار التكلفة: لا نرفع Redis إلى خطة مدفوعة ولا ننشئ Background Worker مستقلًا في هذه المرحلة، لأن الهدف الحالي هو البقاء بدون دفع.

### مراجعة الأمن والأداء وCI — مكتملة ومتحققة — 2026-09-26

- Supabase Security Advisor: لا توجد ملاحظات `RLS Disabled` حرجة؛ RLS مفعّل على 34/34 جدولًا. الملاحظة الحالية `RLS Enabled No Policy` مقصودة لأن التطبيق يستخدم اتصال PostgreSQL مباشرًا ولا يعتمد على Supabase Data API، لذلك لم نضف سياسات تخمينية.
- Supabase Performance Advisor: تم إصلاح جميع علاقات Foreign Key التي ظهرت بلا فهرس مباشر بإضافة 4 فهارس تغطية مناسبة. بقيت ملاحظات `unused_index` فقط، وهي معلوماتية وقد تتغير مع نمو الاستخدام.
- GitHub CI: يتحقق من اختبارات backend/frontend، `pip-audit`، migrations، build، وCompose configuration.
- CodeQL: مفعّل لـPython وJavaScript/TypeScript مع `security-extended` على pushes وPRs وجدولة أسبوعية.
- Production Smoke وProduction DB Backup: كلاهما موجودان بجدولة/تشغيل يدوي ومتحققان تشغيليًا.

### المرحلة B — Production Hardening

الحالة: **قيد التنفيذ**

الهدف: تحويل الأساس الإنتاجي الحالي إلى منصة أكثر صلابة قبل إضافة ميزات كبيرة جديدة.

#### B1 — Rate Limiting واستهلاك الموارد: **مكتمل ومتحقق**

- Global rate limit عبر Redis.
- حدود منفصلة لمسارات المصادقة الحساسة.
- حدود يومية لـAPI keys مع عملية Redis ذرية.
- سياسة fail-open للحد العام عند تعطل Redis، وfail-closed للمسارات الحساسة في الإنتاج.
- التحقق من ownership لمسارات API keys.
- اختبارات CI ناجحة على هذه الأجزاء.

#### B2 — Observability / Readiness: **مكتمل ومتحقق**

- `X-Request-ID` validation/generation/propagation موجود.
- Request metrics logging يربط request ID بسياق الطلب.
- `/health` بقي Liveness check مستقلًا.
- أضيف `/ready` كـDeep Readiness check لقاعدة البيانات وRedis.
- اختبارات الوحدة تغطي حالتي readiness الناجحة والفاشلة.
- Production Smoke أصبح يفحص `/ready` مع retries مناسبة لـRender Free.
- commit `e14cf2e4b517282c69ae70f8eefb221e764ba831` أصبح **live** على Render.
- CodeQL وPublish backend image للcommit الجديد نجحا.
- CI الكامل للcommit `ae5e4dede12dc03ff0179d618f6b8424601fc6c3` أُغلق بنجاح: Backend `pytest`، Frontend tests/build، Production Compose، Production Smoke، CodeQL، وPublish backend image كلها ناجحة.

#### B3 — IDOR/BOLA: **مراجعة أولية واختبارات تكاملية واسعة موجودة**

تمت مراجعة واختبارات cross-user على الموارد والمسارات الحساسة، بما في ذلك:

- Conversations: القراءة، pin، branch، duplicate، bookmarks وغيرها.
- Workspaces: منع استخدام workspace لمستخدم آخر.
- Projects: ownership والمشاركة والربط مع workspace.
- Assistants: CRUD، versions، analytics، وعدم كشف المساعد الخاص لمستخدم آخر.
- Files: القراءة/التنزيل/الحذف، وقيود workspace/project membership.
- Conversation sharing: إنشاء/عرض/إلغاء روابط المشاركة من المالك فقط.
- API keys: منع الإدارة من مستخدم آخر.
- Sessions: منع التحكم في جلسات مستخدم آخر.
- Tags, folders, notifications, scheduled-task history وغيرها من موارد المستخدم.

لا يوجد في المراجعة الحالية مسار IDOR/BOLA واضح غير مغطى؛ يبقى توسيع الاختبارات ممكنًا عند إضافة موارد أو مسارات جديدة.

#### B4 — CI/CD والتحقق التشغيلي: **مكتمل إلى حد كبير ومتحقق**

- Backend/frontend tests.
- `pip-audit`.
- Alembic migrations.
- Production Compose validation.
- CodeQL.
- Production Smoke.
- Production DB Backup.
- retries في Smoke للتعامل مع cold starts على Render Free.

#### B5 — التكلفة والموارد: **مستمر**

- Render Backend: Free.
- Render Frontend: Free.
- Render Redis: Free.
- Supabase production DB: إعداد مجاني حاليًا.
- لا توجد ترقية أو مورد مدفوع ضمن هذه المرحلة.
- Custom Domain وفصل worker المستقل مؤجلان حتى توجد حاجة وميزانية.

### ترحيل PostgreSQL — مكتمل ومتحقق — 2026-09-26

- تم إنشاء Supabase مجانًا بدون مورد مدفوع.
- تم استعادة نسخة PostgreSQL إلى Supabase والتحقق من تطابق **34/34 جدولًا** في `public` مع قاعدة Render.
- تم تحويل `DATABASE_URL` للإنتاج إلى Supabase Session Pooler.
- Production Smoke بعد التحويل: **نجح**.
- Production DB Backup بعد التحويل إلى Supabase: **نجح**.
- تم تفعيل RLS على **34/34 جدولًا** في `public` كحماية لطبقة Supabase Data API، بدون إضافة سياسات تخمينية قد تتعارض مع نموذج صلاحيات التطبيق. التطبيق يستخدم اتصال PostgreSQL مباشرًا من الـbackend.
- بقي تحذير غير حرج: امتداد `vector` موجود في schema `public` بسبب متطلبات استعادة النسخة الحالية؛ لا يتم نقله الآن حتى لا نخاطر بوظائف embeddings. يُراجع لاحقًا عند توفر نافذة آمنة للتعديل.
- Render PostgreSQL القديم لا يزال احتياطي رجوع مؤقتًا حتى 2026-10-10.


### المرحلة C — Product UX

الحالة: **قيد التنفيذ — C1 وC2 مكتملان، وC3 جارٍ**

الهدف: تحسين تجربة الاستخدام اليومية مع الحفاظ على المعمارية الحالية، نظام Toast العالمي، اختبارات الواجهة، وعدم إضافة موارد مدفوعة.

#### C1 — Global error feedback: **مكتمل ومتحقق**
- تم استبدال رسائل الخطأ المعروضة عبر `window.alert` في إجراءات Workspace الأساسية باستخدام Global Toast.
- تم نشر التغيير على Render Frontend والتحقق من Production Smoke.

#### C2 — Workspace member action errors: **مكتمل ومتحقق**
- أخطاء تحميل بيانات Workspace.
- دعوات الأعضاء.
- تحديث الأدوار.
- إزالة الأعضاء.
- إلغاء الدعوات.
- تحديث النموذج الافتراضي والحصة اليومية.
- تصدير CSV للاستخدام.
- تمت إضافة اختبارات UI لأحداث `app:toast` للحالات الجديدة.
- الإصلاح النهائي في commit `ae5e4dede12dc03ff0179d618f6b8424601fc6c3`.
- Render Frontend للـcommit النهائي أصبح **live**.
- CI النهائي للـcommit نجح بالكامل.

#### C3 — Workspace shared conversations error feedback: **مكتمل ومتحقق**
- فشل تحميل المحادثات المشتركة في `WorkspaceSharedConversationsPanel` لم يعد يتحول إلى قائمة فارغة بصمت؛ أصبح يرسل Global Toast برسالة API أو رسالة fallback.
- تمت إضافة اختبار UI يتأكد من إرسال `app:toast` عند فشل التحميل.
- commit الدمج `129054c476b85159560474abdd6fd0ba47151f1a`.
- CI النهائي نجح بالكامل: Backend `pytest`، Frontend tests/build، Production Compose.
- CodeQL نجح.
- Production Smoke نجح.
- Render Frontend للـcommit أصبح **live**.

#### C3 — Assistant Knowledge load error feedback: **مكتمل ومتحقق**
- فشل تحميل ملفات معرفة المساعد في `AssistantEditor` لم يعد يتحول إلى حالة فارغة صامتة؛ أصبح يرسل Global Toast برسالة مترجمة.
- تمت إضافة مفتاحي ترجمة عربي/إنجليزي ورسالة اختبارية للحالة.
- تمت إضافة اختبار UI يتأكد من إرسال `app:toast` عند فشل تحميل ملفات المعرفة.
- commit الدمج `2914e8df4939adc55da6aa09bb87bf89bb2c255e`.
- CI النهائي نجح بالكامل: Backend `pytest`، Frontend tests/build، Production Compose.
- CodeQL نجح.
- Production Smoke نجح.
- Render Frontend للـcommit أصبح **live**.

#### C3 — الخطوة التالية
مراجعة مسار UX آخر خارج Workspace وAssistant Knowledge، مع أولوية للشاشات التي تخفي فشل API أو تعرض حالة خطأ محلية بدل Global Toast عندما يكون Toast هو النمط المناسب.
