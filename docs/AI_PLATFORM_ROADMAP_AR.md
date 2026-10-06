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

الحالة: **مستقرة تشغيليًا — الأساس الإنتاجي مكتمل، مع نقاط اختيارية مؤجلة**

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
- Observability: **مكتمل تشغيليًا** — `X-Request-ID` مرتبط بسياق logging، وProduction Smoke يتحقق من propagation، و`/ready` يفحص DB + Redis. أي تحسينات إضافية للمراقبة لاحقة وليست blocker.

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

الحالة: **مكتملة ومتحققة**

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

#### B3 — IDOR/BOLA: **مكتمل ومتحقق**

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

### تحقق B3 النهائي — 2026-09-27
- تمت إضافة اختبارات cross-user مخصصة لـ **Project Memories** و**Assistant Workspace Sharing** في PR #299.
- تم تصحيح اختبار دعوة عضو المشروع ليستخدم مسار قبول الدعوة الفعلي ويلتقط token عبر mock لإرسال البريد.
- PR #299 تم دمجه بنجاح بعد نجاح الفحوصات.
- CI run `3059` (GitHub Actions run `36334506819`): **نجح**.
- CodeQL run `333` (GitHub Actions run `36334506818`): **نجح**.
- commit الدمج بعد squash: `ac88c1cc6f79744bab99f733692caa496ed3b9e4`.
- النتيجة: **B3 مغلق ومتحقق**؛ لا توجد حاليًا مسارات IDOR/BOLA معروفة غير مغطاة ضمن نطاق المراجعة الحالي.

### تحقق Stage B النهائي — 2026-09-27
- B1 — Rate Limiting واستهلاك الموارد: **مكتمل ومتحقق**.
- B2 — Observability / Readiness: **مكتمل ومتحقق**.
- B3 — IDOR/BOLA: **مكتمل ومتحقق**.
- B4 — CI/CD والتحقق التشغيلي: **مكتمل ومتحقق**.
- B5 — التكلفة والموارد: **مكتمل ومتحقق حاليًا**، مع متابعة انتهاء Render PostgreSQL المؤقت في 2026-10-10.
- القرار: **Stage B مغلقة**، ولا توجد حاجة الآن لإنشاء مورد مدفوع أو الانتقال إلى خطة مدفوعة.

#### B4 — CI/CD والتحقق التشغيلي: **مكتمل ومتحقق**

- Backend/frontend tests.
- `pip-audit`.
- Alembic migrations.
- Production Compose validation.
- CodeQL.
- Production Smoke.
- Production DB Backup.
- retries في Smoke للتعامل مع cold starts على Render Free.

#### B5 — التكلفة والموارد: **مكتمل ومتحقق حاليًا**

- Render Backend: **Free**.
- Render Frontend: **Free**.
- Render Redis: **Free**.
- Render PostgreSQL القديم المؤقت: **Free**، وبقي فقط كخطة رجوع حتى **2026-10-10**.
- Supabase organization الحالية: **Free**، ومشروع الإنتاج `ai-chat-prod-db` حالته `ACTIVE_HEALTHY`.
- لا توجد ترقية أو مورد مدفوع تم إنشاؤه خلال Stage B.
- Custom Domain وفصل worker المستقل ما زالا مؤجلين حتى توجد حاجة وميزانية.
- نقطة المتابعة التشغيلية المتبقية: بعد **2026-10-10** نتحقق من انتهاء مورد Render PostgreSQL المؤقت وعدم وجود أي مورد مدفوع غير مقصود.

### ترحيل PostgreSQL — مكتمل ومتحقق — 2026-09-26

- تم إنشاء Supabase مجانًا بدون مورد مدفوع.
- تم استعادة نسخة PostgreSQL إلى Supabase والتحقق من تطابق **34/34 جدولًا** في `public` مع قاعدة Render.
- تم تحويل `DATABASE_URL` للإنتاج إلى Supabase Session Pooler.
- Production Smoke بعد التحويل: **نجح**.
- Production DB Backup بعد التحويل إلى Supabase: **نجح**.
- تم تفعيل RLS على **34/34 جدولًا** في `public` كحماية لطبقة Supabase Data API، بدون إضافة سياسات تخمينية قد تتعارض مع نموذج صلاحيات التطبيق. التطبيق يستخدم اتصال PostgreSQL مباشرًا من الـbackend.
- بقي تحذير غير حرج: امتداد `vector` موجود في schema `public` بسبب متطلبات استعادة النسخة الحالية؛ لا يتم نقله الآن حتى لا نخاطر بوظائف embeddings. يُراجع لاحقًا عند توفر نافذة آمنة للتعديل.
- Render PostgreSQL القديم لا يزال احتياطي رجوع مؤقتًا حتى 2026-10-10.



## المرحلة D — Agent Platform

الحالة: **مكتملة ومتحققة — D1 إلى D8**

### D2 — MCP Integration: **مكتمل ومتحقق**
- تمت إضافة MCP Python SDK `2.2.0`.
- التكامل اختياري ومغلق افتراضيًا عبر `MCP_ENABLED=false`.
- دعم Streamable HTTP لخوادم MCP المصرح بها.
- اكتشاف أدوات MCP ودمجها داخل Tool Registry scoped لكل تشغيل Agent.
- حدود لعدد الخوادم والأدوات، وHTTPS إلزامي في production.
- أضيفت اختبارات للإعداد والاكتشاف وتنفيذ أداة MCP.
- PR #305 تم دمجه بنجاح.
- CI run `3095`: **نجح**.
- CodeQL run `345`: **نجح**.
- commit الدمج بعد squash: `f47e065da4beadc7bceb5a293fa6062d81c158ec`.

### D1 — Tool Registry: **مكتمل ومتحقق**
- تم إنشاء Registry مركزي لتعريف الأدوات واكتشافها وتنفيذها.
- الأدوات الحالية المسجلة: `calculator`، `python`، `web_search`، `analyze_data`.
- تم نقل Agent Mode لاستخدام الـRegistry بدل التعريف والتنفيذ الموزع داخل `ai_agent.py`.
- تمت إضافة اختبارات للـregistry، منع أسماء الأدوات المكررة، والتعامل مع الأدوات غير المسجلة.
- PR #303 تم دمجه بنجاح.
- CI run `3080`: **نجح**.
- CodeQL run `341`: **نجح**.
- commit الدمج بعد squash: `5330b0ff6064072aa434cd200a7fecda89e19624`.

### D4 — Tool Permissions: **مكتمل ومتحقق**
- أضيفت `AGENT_ALLOWED_TOOLS_JSON` كقائمة سماح صريحة للأدوات التي يمكن أن يعرّفها Agent للـmodel.
- أصبح `ToolRegistry` يدعم allowlist حقيقية ويمنع تسجيل أداة خارج الصلاحيات قبل ظهورها للـmodel.
- تم تطبيق الـallowlist داخل `AgentRuntime` قبل تسجيل أي أداة MCP مكتشفة.
- أدوات MCP لا تُكشف تلقائيًا؛ كل خادم يتطلب `allowed_tools` بأسماء الأدوات البعيدة بشكل صريح، إضافة إلى allowlist العامة.
- تم توثيق الإعدادات في `.env.example`.
- أضيفت اختبارات للصلاحيات في Registry وAgent Runtime وMCP discovery.
- PR #308 تم دمجه بنجاح.
- CI run `3126`: **نجح**.
- CodeQL run `356`: **نجح**.
- commit الدمج بعد squash: `82f4e295c1c8fe064fef91131adaee17d87a19bf`.

### D3 — Agent Runtime: **مكتمل ومتحقق**
- تم فصل دورة تشغيل Agent عن طبقة النقل HTTP داخل `ai-backend/app/services/agent_runtime.py`.
- الـRuntime يعيد نتيجة موحدة تتضمن `run_id` والحالة والنص والمصادر والـtokens وعدد الجولات واستدعاءات الأدوات.
- تم الإبقاء على الحدود الآمنة الحالية: 3 جولات، 4 استدعاءات أدوات لكل جولة، وحدّ لحجم نتائج الأدوات وسجل المحادثة.
- أضيفت مهلة مستقلة لتنفيذ كل أداة مع معالجة timeout/cancellation والأخطاء الداخلية دون إسقاط تشغيل Agent بالكامل.
- أضيفت أحداث lifecycle للتشغيل والجولات والميزانية والإكمال، مع الحفاظ على أحداث الأدوات الحالية.
- تم ربط `ai_agent.py` بالـRuntime الجديد مع الحفاظ على واجهة الاستدعاء الحالية للتطبيق.
- أضيفت اختبارات مخصصة لدورة التشغيل، المهلة، lifecycle، وحدود التنفيذ.
- PR #307 تم دمجه بنجاح بعد إصلاح اختبارات async وsnapshot الرسائل.
- CI run `3113`: **نجح**.
- CodeQL run `353`: **نجح**.
- commit الدمج بعد squash: `d6c8a743d257b035b79814edb019b8fe47aaad15`.

### D4 — Tool Permissions: **مكتمل ومتحقق**
- تمت إضافة Allowlist عالمية لأدوات Agent عبر `AGENT_ALLOWED_TOOLS_JSON`.
- الـTool Registry يرفض تسجيل الأدوات غير المسموح بها، وRuntime لا يعرض للـmodel إلا الأدوات المسموح بها.
- خوادم MCP لا تعرض أي أداة remote تلقائيًا؛ كل خادم يحتاج `allowed_tools` صريحة بأسماء الأدوات البعيدة المسموح بها.
- أضيفت اختبارات مستقلة لـRegistry permissions وAgent runtime filtering وMCP server allowlists.
- PR #308 تم دمجه بنجاح.
- CI run `3126`: **نجح**.
- CodeQL run `356`: **نجح**.
- commit الدمج بعد squash: `82f4e295c1c8fe064fef91131adaee17d87a19bf`.

### D5 — Sandboxed Code Execution: **مكتمل ومتحقق**
- المنفّذ الحالي يعمل داخل عملية Python منفصلة مع AST allowlist قبل التنفيذ.
- الاستيراد، الوصول للملفات، التنفيذ الديناميكي، attribute access المحظور، وتعريف الدوال/الأصناف غير مسموحة.
- تم تقييد البيئة: stdin مغلق، globals محدودة، ولا تُمرّر متغيرات البيئة الحساسة إلى worker.
- توجد حدود واضحة للكود والناتج ووقت التنفيذ، مع Linux resource limits للـCPU والذاكرة وحجم الملفات وعدد الملفات المفتوحة ومنع core dumps.
- عند تجاوز المهلة يتم إنهاء مجموعة العملية كاملة بدل ترك worker يعمل في الخلفية.
- أضيفت اختبارات أمنية مباشرة لرفض constructات خطرة، إيقاف الحلقة اللانهائية، حد طول الكود، وعدم كشف مسارات المضيف في أخطاء التنفيذ.
- PR #327 تم دمجه بنجاح.
- CI run `3328`: **نجح**.
- CodeQL run `411`: **نجح**.
- commit الدمج بعد squash: `6d4bb58e7684c906fe7809b890f88d9f46da9b5a`.

### D4 — Tool Permissions: **مكتمل ومتحقق**
- تمت إضافة Allowlist صريحة لأدوات Agent عبر `AGENT_ALLOWED_TOOLS_JSON`.
- الـTool Registry يفرض الـallowlist عند التسجيل والعرض، فلا تصل الأداة غير المسموح بها إلى تعريفات النموذج.
- خوادم MCP أصبحت تتطلب `allowed_tools` صريحة لكل أداة بعيدة؛ أدوات MCP غير المدرجة لا تُكتشف ولا تُعرض للـAgent.
- بقي التكامل افتراضيًا مغلقًا، وHTTPS مطلوب في production كما في D2.
- أضيفت اختبارات للـRegistry والـRuntime وMCP للتحقق من المنع والسماح.
- PR #308 تم دمجه بنجاح.
- CI run `3126`: **نجح**.
- CodeQL run `356`: **نجح**.
- commit الدمج بعد squash: `82f4e295c1c8fe064fef91131adaee17d87a19bf`.

### D6 — Long-running Agent Jobs: **مكتمل ومتحقق**
- تم إنشاء نموذج persisted باسم `agent_jobs` مع حالات `queued` و`running` و`succeeded` و`failed` و`cancelled`، ومؤشرات للحالة والمستخدم وworkspace والـCelery task.
- أضيفت واجهة `POST /agent-jobs` التي ترجع `202 Accepted` بدل تشغيل Agent داخل طلب HTTP، مع endpoints للقائمة وpolling والإلغاء التعاوني.
- التنفيذ الخلفي يستخدم Celery وRedis الموجودين أصلًا، دون إنشاء Worker أو مورد مدفوع جديد.
- Job التنفيذ يستخدم `AgentRuntime` وTool Permissions الحالية، ويتحقق من عضوية workspace وحصة AI وميزانية التكلفة قبل التشغيل.
- النتيجة تُحفظ في محادثة حقيقية مع `run_id` والمصادر والـtokens، ويُسجل الاستهلاك في `UsageLog`.
- تمت إضافة migration `0066_agent_jobs` واختبارات lifecycle للعزل والإنشاء والإلغاء والتنفيذ.
- PR #311 تم دمجه بنجاح بعد إصلاح عرض `celery_task_id` وإعادة استخدام transaction الاختبار.
- CI run `3154`: **نجح** بالكامل.
- CodeQL run `367`: **نجح** بالكامل.
- commit الدمج بعد squash: `a12e5b08af51746042b78ff2acf2c7def8a4c3d4`.
- تحقق Render التشغيلي بعد الدمج: خدمة الـbackend بدأت نشر commit `a12e5b08…`، وlogs تؤكد تنفيذ migration `0065_object_storage → 0066_agent_jobs`، وبدء Embedded Celery Worker وBeat، ونجاح `/health` عدة مرات بحالة `200` على instance الجديد. حالة Render deploy API بقيت `update_in_progress` في آخر استعلام رغم أن instance الجديد كان يخدم الطلبات بنجاح.

### D7 — Scheduled Agents: **مكتمل ومتحقق**
- أضيف `execution_mode=standard|agent` إلى المهام المجدولة، مع بقاء `standard` هو الافتراضي للمهمات الحالية.
- عند حلول موعد مهمة بوضع `agent` يتم إنشاء `AgentJob` persisted وربطه بـ`ScheduledTaskRun` ثم وضعه في Celery/Redis الموجودين أصلًا.
- أضيفت migration `0067_scheduled_agents` لإضافة وضع التنفيذ وربط سجل الجدولة بالـAgent Job.
- يتم تحديث `ScheduledTaskRun` عند اكتمال Agent أو فشله/إلغائه، مع إبقاء سجل المحادثة والـrun_id والنتيجة ضمن مسار Agent نفسه.
- واجهات إنشاء وتعديل المهام المجدولة تعرض وتقبل وضع Agent، مع اختبار للعزل وربط سجل الجدولة بالـjob.
- PR #312 تم دمجه بنجاح.
- CI run `3170`: **نجح** بالكامل.
- CodeQL run `370`: **نجح** بالكامل.
- commit الدمج بعد squash: `08a5c0ff7ac5e0eb5e4918dfc1d05c7751a6c84d`.
- لا توجد موارد مدفوعة جديدة؛ D7 يعيد استخدام Celery وRedis الموجودين.

### D5 — Sandboxed Code Execution: **مكتمل ومتحقق**
- أداة Python تعمل داخل process منفصل باستخدام Python isolated mode (`-I`) مع `-S` و`-B` وبيئة تشغيل دنيا.
- AST allowlist تمنع imports، attribute access، dynamic evaluation، definitions، comprehensions، وميزات خطرة أخرى قبل التنفيذ.
- لا توجد filesystem/network imports، و`__builtins__` معطلة داخل worker.
- حدود تشغيل حالية: 2 ثانية، 256MB ذاكرة افتراضية، 1MB لحجم الملفات، و16 file descriptors مع output limit 12,000 حرف.
- الاختبارات الإضافية تغطي محاولات `__import__` و`eval` والوصول إلى builtins وattributes وcomprehensions وحد الناتج.
- PR #310 تم دمجه بنجاح.
- CI run `3134`: **نجح** بالكامل.
- CodeQL run `360`: **نجح**.
- commit الدمج بعد squash: `705a5b6e3b924a49322805c1e2dbdf03dd073c36`.
- ملاحظة معمارية: هذا sandbox على مستوى Python/process وresource limits، وليس container/kernel isolation كاملًا؛ لذلك يبقى فصل code-runner في container مستقل خيارًا لاحقًا عند الحاجة.

### D8 — Prompt-injection / Tool-abuse defenses: **مكتمل ومتحقق**
- أضيفت طبقة أمن مشتركة للتحقق من tool arguments عبر JSON schema مبسط، وحجم أقصى `12,000` حرف، وعمق أقصى `8` مستويات.
- تم تصنيف مخرجات Web Search وData Analysis وMCP كـuntrusted data، مع اكتشاف أنماط شائعة لـprompt injection.
- مخرجات الأدوات غير الموثوقة تُمرر إلى model داخل حدود بيانات صريحة، ولا تُعامل كتعليمات.
- بعد وصول محتوى غير موثوق، يمنع Agent Runtime أي tool chaining إضافي ويطلب ردًا نهائيًا بدون أدوات.
- أضيفت اختبارات للصلاحيات، رفض arguments غير الصالحة أو الكبيرة، كشف prompt injection، تغليف untrusted output، ومنع متابعة استدعاءات الأدوات بعد المحتوى غير الموثوق.
- PR #313 تم دمجه بنجاح.
- CI run `3185`: **نجح** بالكامل.
- CodeQL run `373`: **نجح** بالكامل.
- commit الدمج بعد squash: `4d9a2f17d03cbad9397aa40b597f3b26673bd157`.



1. Tool Registry
2. MCP integration
3. Agent runtime
4. Tool permissions
5. Sandboxed code execution
6. Long-running agent jobs
7. Scheduled agents
8. Prompt-injection / tool-abuse defenses

## المرحلة E — Platform & Developer Ecosystem

الحالة: **مكتملة ومتحققة — E1 إلى E8**

### E1 — API Keys: **مكتمل ومتحقق**
- إدارة مفاتيح Developer API موجودة عبر `GET /api-keys` و`POST /api-keys` و`DELETE /api-keys/{key_id}`.
- السر الكامل للمفتاح (`ak_live_...`) يُعاد عند الإنشاء فقط، بينما قاعدة البيانات تخزن `SHA-256` hash وprefix فقط.
- المفاتيح تدعم الإلغاء، انتهاء الصلاحية، حدًا متدحرجًا للطلبات، ومراقبة الاستخدام عبر `GET /api-keys/{key_id}/usage`.
- نقطة Developer API الحالية هي `POST /v1/chat` وتستخدم `X-API-Key` مع التحقق من حالة الحساب والملكية وعزل موارد المستخدم.
- تسجيل الاستخدام يرتبط بالمفتاح نفسه (`api_key_id`) لدعم التحليلات والحصص.
- واجهة Account Settings توفر إنشاء المفتاح ونسخ السر وإلغاءه وعرض استخدامه.
- أضيفت اختبارات شاملة للإنشاء، المصادقة، الإلغاء، الانتهاء، العزل بين المستخدمين، الاستخدام، والـrate limit.
- CI وCodeQL اللذان يغطيان هذه المكونات نجحا ضمن التحققات الحالية على `main`.

### E2 — API Versioning: **مكتمل ومتحقق**
- تم تثبيت Developer API الحالي كإصدار `v1` مع نقطة اكتشاف `GET /v1`.
- بقي `POST /v1/chat` هو المسار المستقر للمطورين.
- الاستجابات الناجحة من `/v1/chat` تحمل `X-API-Version: v1`.
- تمت إضافة سياسة توافق واضحة: التغييرات الكاسرة تتطلب إصدار URL رئيسيًا جديدًا مثل `/v2`، بينما الإضافات غير الكاسرة يمكن أن تبقى داخل الإصدار نفسه.
- تم توثيق الفصل بين Developer API versioning ومسارات إدارة المفاتيح مثل `/api-keys`.
- أضيفت اختبارات لاكتشاف الإصدار والتحقق من ترويسة الإصدار.
- PR #317 تم دمجه بنجاح.
- CI run `3211`: **نجح**.
- CodeQL run `380`: **نجح**.
- commit الدمج بعد squash: `ba948ae101a5feee94c29738a040939952a430c2`.

### E3 — Developer Webhooks: **مكتمل ومتحقق**
- تمت إضافة إدارة Webhook endpoints للمطورين تحت `/webhooks` مع عزل كامل حسب المستخدم.
- secret الخاص بالـWebhook يُعاد عند الإنشاء أو تدويره فقط، ويُخزن مشفرًا في قاعدة البيانات.
- كل delivery يستخدم HMAC-SHA256 مع `X-Webhook-Id` و`X-Webhook-Event` و`X-Webhook-Timestamp` و`X-Webhook-Signature`.
- تم تطبيق تحقق SSRF على وجهة الـWebhook: رفض localhost والشبكات الداخلية والعناوين غير العامة، مع إلزام HTTPS في production ومنع redirects.
- تمت إضافة سجل persisted للـdeliveries مع حالات المحاولة والنتيجة والـHTTP status والـretry schedule.
- retry محدود إلى 5 محاولات مع backoff، ويستخدم Celery/Redis الموجودين أصلًا دون إنشاء مورد مدفوع جديد.
- أحداث Developer API الحالية: `api_key.created` و`api_key.revoked`، إضافة إلى `webhook.test` للتحقق اليدوي من endpoint.
- أضيفت واجهة اختبار endpoint وقائمة deliveries، مع تدوير secret.
- تمت إضافة migration `0068_developer_webhooks` واختبارات E3 للأمان والعزل والتوقيع والتسليم.
- PR #318 تم دمجه بنجاح.
- CI run `3232`: **نجح** بالكامل.
- CodeQL run `384`: **نجح**.
- commit الدمج بعد squash: `e684a55585a90404d72a64c1ee64d88ec1404ae3`.

### E4 — OAuth / Connectors: **مكتمل ومتحقق**
- تمت إضافة أساس OAuth 2.0 قابل للتفعيل اختياريًا لمزوّدي Google وMicrosoft.
- تدفق التفويض يستخدم Authorization Code مع PKCE S256 وstate أحادي الاستخدام مع صلاحية زمنية.
- حالات OAuth وcode verifiers تُخزّن في PostgreSQL، والأسرار وaccess/refresh tokens تُخزن مشفرة باستخدام Fernet.
- تمت إضافة اكتشاف المزودين المهيئين، بدء/إكمال التفويض، إدارة الاتصالات، تحديث tokens، والفصل، مع عزل كامل حسب المستخدم.
- أضيفت migration `0069_oauth_connectors` ونماذج `oauth_connections` و`oauth_states` واختبارات lifecycle وإعادة استخدام state والعزل والتحديث.
- مزودو OAuth يبقون معطلين افتراضيًا حتى تُضبط بيانات الاعتماد من الخادم؛ لا توجد حاجة لمورد Render أو Supabase مدفوع.
- أضيف تحقق production يلزم `OAUTH_CALLBACK_BASE_URL` عبر HTTPS عند تفعيل موفّر OAuth.
- تم تعزيز منع replay المتزامن لقيمة state باستخدام قفل صف PostgreSQL أثناء الاستهلاك.
- PR #320 تم دمجه بنجاح.
- CI run `3266`: **نجح** بالكامل.
- CodeQL run `392`: **نجح**.
- commit الدمج بعد squash: `9a537eb5a77c6fbf20667eae25ed1b1df9c3c8e6`.

### E5 — Python + JavaScript SDKs: **مكتمل ومتحقق**
- تمت إضافة SDK رسمي للـPython داخل `sdk/python` باسم الحزمة `ai-chat-saas`، مع دعم Python 3.9+، وعميل `AIChatClient` لنقطة `POST /v1/chat`.
- تمت إضافة SDK رسمي للـJavaScript داخل `sdk/javascript` باسم الحزمة `ai-chat-saas`، مع دعم Node.js 18+ واستخدام `fetch` المدمج.
- كلا الـSDKs يستخدمان عقد Developer API `v1` نفسه، والمصادقة `X-API-Key`، ويقدمان نماذج رد واضحة ومعالجة أخطاء typed مع `X-Request-ID` و`Retry-After` عند توفرها.
- أضيفت اختبارات مستقلة للـPython والـJavaScript SDKs، وأصبح CI يشغل حزمة SDK الخاصة بهما إلى جانب اختبارات backend/frontend وProduction Compose.
- CI run `3290`: **نجح** بالكامل، بما في ذلك اختبارات Python SDK وJavaScript SDK.
- CodeQL run `397`: **نجح** لـPython وJavaScript/TypeScript.
- PR #324 تم دمجه بنجاح.
- commit الدمج بعد squash: `05910814f0a0edf2c527a1da9e98540df5197bf8`.
### E7 — Usage / billing / cost controls: **مكتمل ومتحقق**
- Usage Logs مرتبطة بالمستخدم وWorkspace وAPI key مع input/output tokens وprovider/model وlatency لدعم التحليلات والحصص.
- Developer API وBilling يعرضان الاستخدام والحدود اليومية، مع `API key` usage مستقل وعزل حسب المالك.
- أضيف تسعير قابل للتهيئة عبر `AI_PRICING_JSON`؛ عندما لا يتوفر سعر معروف لا يتم تخمين تكلفة مالية، وتظهر الطلبات غير المسعّرة بوضوح في التحليلات.
- يوجد guardrail للميزانية الشهرية العامة عبر `AI_MONTHLY_BUDGET_USD` يمنع المستخدمين غير الإداريين من بدء طلبات AI بعد تجاوز الميزانية المهيأة.
- لكل Workspace حد يومي اختياري وميزانية AI شهرية اختيارية، مع منع التجاوز قبل الطلب وتدقيق التغيير.
- `/billing/usage` و`/workspaces/{id}/usage` وتحليلات Admin للتكلفة والميزانية توفّر الاستخدام الحالي، تكلفة الشهر، المتبقي، والطلبات غير المسعّرة، مع CSV للاستخدام.
- واجهات Billing وWorkspace وAdmin تعرض usage/cost guardrails، مع اختبارات backend/frontend للصلاحيات والحسابات وحالات التسعير غير المعروف.
- لا توجد موارد مدفوعة جديدة مطلوبة لهذه الوظائف؛ تعتمد على PostgreSQL/Redis الموجودين.

### E6 — Enterprise RBAC: **مكتمل ومتحقق**
- تم إضافة RBAC على مستوى مساحة العمل مع أدوار مخصصة محفوظة في PostgreSQL، وصلاحيات مسماة مثل `members.read` و`members.invite` و`members.manage` و`rbac.manage` وغيرها.
- الأدوار المخصصة تُنشأ وتُعدّل وتُحذف من خلال API مخصص، ولا يمكن للمستخدم منح أو تعيين صلاحيات تتجاوز صلاحياته الحالية.
- أصبح بالإمكان إسناد دور RBAC مخصص لعضو غير المالك، مع منع تعيين الدور المخصص للمالك.
- تم توحيد فحص صلاحيات أعضاء مساحة العمل بدل الاعتماد فقط على `owner/admin/member` في المسارات المغطاة، مع الحفاظ على سلوك الأدوار القديمة كـfallback.
- أضيفت واجهات لاكتشاف permission catalog وإدارة roles وتعيين/إزالة الدور عن العضو.
- تمت إضافة migration `0070_enterprise_rbac` مع foreign key اختياري من `workspace_members` إلى دور RBAC.
- أضيفت اختبارات للعزل، إنشاء الدور، منع تصعيد الصلاحيات، تعيين الدور، ومنع أعضاء الدور المحدود من إدارة RBAC.
- PR #328 تم دمجه بنجاح بعد نقل E6 إلى أحدث `main` وإصلاح اختبار تصادم invitation token.
- CI run `3342`: **نجح بالكامل**.
- CodeQL run `414`: **نجح بالكامل**.
- commit الدمج بعد squash: `57dd468eef3aaf1140dd86f14109a8ebfe4c2d1b`.
- PR #326 القديم أُغلق باعتباره superseded ولا يحمل تغييرًا إضافيًا على `main`.
- لا توجد أي موارد مدفوعة جديدة ضمن E6.
### E8 — Versioning for assistants, prompts, knowledge bases and agents: **مكتمل ومتحقق**
- Assistant versions أصبحت snapshots غير قابلة للتعديل تتضمن إعدادات المساعد، قائمة ملفات المعرفة المرتبطة، وtool-policy snapshot.
- استرجاع نسخة Assistant يعيد أيضًا snapshot ملفات المعرفة التي ما تزال مملوكة للمستخدم، ثم ينشئ version جديدة بدل تعديل التاريخ القديم.
- Saved Prompts أصبحت تمتلك تاريخ versions immutable مع endpoints للعرض والاسترجاع، والاسترجاع ينشئ version جديدة.
- AgentJob يحفظ `agent_version` مشتقًا من runtime/tool-policy/limits، إضافة إلى `tool_policy_snapshot`، بحيث تبقى المهمة قابلة للتتبع حتى عند تغيّر الإعدادات لاحقًا.
- Scheduled Agent jobs تستخدم نفس snapshot عند إنشاء AgentJob.
- تمت إضافة migration `0072_platform_asset_versioning` بعد `0071_workspace_cost_controls` لضمان سلسلة Alembic واحدة بدون multiple heads.
- PR #331 تم دمجه بنجاح بعد إصلاح سلسلة migration.
- CI run `3398`: **نجح** بالكامل، بما في ذلك Alembic وpytest.
- CodeQL run `427`: **نجح** بالكامل لـPython وJavaScript/TypeScript.
- commit الدمج بعد squash: `4c8d52dd89ec828fed5f2aff3e18f1be18ca2b31`.
- لا توجد موارد مدفوعة جديدة ضمن E8.

1. API Keys
2. API versioning
3. Webhooks
4. OAuth / connectors
5. Python + JavaScript SDKs
6. Enterprise RBAC
7. Usage / billing / cost controls
8. Versioning for assistants, prompts, knowledge bases and agents

### المرحلة C — Product UX

الحالة: **C1 وC2 وC3 مكتملة ومتحققة**

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

#### C3 — Global Toast / API error feedback: **مكتمل ومتحقق**
تم توحيد مسارات أخطاء API الرئيسية في الواجهة ضمن Global Toast مع اختبارات UI، بدل ترك فشل التحميل أو الإجراءات يتحول إلى حالة فارغة أو خطأ محلي بصمت.

النطاق الذي تم تغطيته يشمل:
- Workspace/shared conversations وعمليات التعليقات.
- Files وعمليات الرفع/الإرفاق/الفصل/الحذف/المعاينة.
- Admin Dashboard، Pricing/Billing، Scheduled Tasks، Account Settings.
- Public Assistant وModel Compare وConversation Share Manager.
- تحميل المحادثات وProjects وAssistants وAI Models وبيانات الـsidebar وبيانات المستخدم.
- AssistantEditor: المعرفة، سجل النسخ، Analytics، إعدادات الرابط العام، المقارنة، وعمليات تفعيل/تدوير/تعطيل الرابط العام.
- ProjectEditor: تحميل/إضافة/تعديل/حذف ذاكرة المشروع.

### تحقق C3 النهائي — 2026-09-27
- PRs الأخيرة #295 و#296 و#297 تم دمجها بنجاح.
- CI وCodeQL نجحا لكل PR من هذه السلسلة.
- آخر Frontend deployment للcommit `a11c01fb03235d1bafc5a4966c82fc447658b1a1` أصبح **live** على Render.
- لا توجد موارد Render مدفوعة أضيفت ضمن C3.
- التدقيق النهائي لمسارات `catch` و`setError` ميّز الحالات التي تحتاج Global Toast عن الحالات المحلية/أفضل جهد، مثل المصادقة، مشاركة محمية بكلمة مرور، clipboard/speech synthesis، وlocal storage.
- الحالة الحالية: **C3 مغلقة**، والخطوة التالية هي اختيار بند المرحلة التالية بعد مراجعة Stage B غير المكتملة؛ لا نفتح ميزة منتج جديدة قبل التعامل مع بند B المطلوب.

## المرحلة F — Agent Product & Project Workspace

الحالة الحالية: **F1 وF2 وF3 مكتملة ومتحققة على `main`**.

### F1 — Agent UX / Runtime Activity: مكتمل
- تم ربط تشغيل Agent داخل المحادثة بأحداث runtime واضحة للجولات، الأدوات، الميزانية، الإلغاء، والتحذيرات والإكمال.
- تم إبقاء حالة الإكمال ظاهرة بعد انتهاء البث، ثم مسحها عند بدء رسالة جديدة.
- PR #354 وPR #355 تم دمجهما في `main`.

### F2 — Project Workspace: مكتمل ومتحقق
#### F2.1 — Persistent Project Files
- أضيفت ملفات مصدر دائمة للمشروع مع CRUD محمي بعزل المشروع والـworkspace.
- أضيفت شجرة ملفات ومحرر داخل `ProjectEditor`.
- تتم مزامنة الملفات التي ينشئها Agent مع شجرة المشروع مع الحفاظ على artifact ZIP الحالي.
- PR #356 تم دمجه في `main`.

#### F2.2 — Agent Project Context & Safe Editing
- أضيفت أدوات Agent: `list_project_files`, `read_project_file`, `search_project_files`, `edit_project_file`.
- الأدوات مقيدة بالمشروع الحالي، مع حدود للحجم والمسارات، وoptimistic concurrency عبر `expected_content`، وإظهار unified diff محدود.
- محتوى المشروع الخارج من الأدوات يُعامل كـuntrusted data حتى لا يتحول إلى تعليمات للنموذج.
- PR #357 وPR #358 تم دمجهما في `main`.
- commit المرحلة قبل F3: `75f12a5485134a9cf4eebffa536a61dd1e99baaa`.

### F3 — Project Validation & Preview: مكتملة ومتحققة
تم إغلاق F3 عبر PR #360 ودمجه إلى `main` في commit:
`05cdd9f3d556b3c6863f96cbfc3cc5b0d7420068`.

#### F3.1 — Read-only Project Validation
- أضيف `GET /projects/{project_id}/validate` مع عزل كامل حسب عضوية المشروع.
- يفحص نوع المشروع، `package.json`، `pyproject.toml`، `requirements.txt`، بنية `index.html`، NUL bytes، وأسماء الملفات التي تبدو أسرارًا أو مفاتيح خاصة.
- يعيد أخطاء وتحذيرات مرتبطة بالملف مع ملخص counts.
- تمت إضافة اختبارات backend للعزل ونتائج التحقق.

#### F3.2 — Safe Static Preview
- أضيفت معاينة `index.html` من داخل `ProjectEditor`.
- المعاينة تستخدم `iframe sandbox=""` بدون `allow-scripts` أو `allow-same-origin` أو `allow-forms`.
- لا يتم تشغيل JavaScript المولّد داخل بيئة التطبيق الرئيسية.
- تمت إضافة اختبارات frontend للتأكد من وجود الـsandbox وعدم منح صلاحية تشغيل السكربتات.

#### تحقق F3
- CI run #3831: **نجح بالكامل** — Backend، Frontend، SDK، Production Compose.
- CodeQL run #596: **نجح بالكامل** لـPython وJavaScript/TypeScript.
- PR #360: **Merged**.
- لا توجد موارد مدفوعة جديدة مطلوبة لـF3.

### F3.3 — Advanced Preview Architecture: **مكتملة ومتحققة — 2026-10-02**
الهدف كان بناء عقد آمن لمعاينة المشاريع التي تحتاج build/runtime بدون تشغيل كود المستخدم داخل origin التطبيق الرئيسي.

ما تم:
- تحليل نوع المشروع وتحديد استراتيجية المعاينة.
- بناء JavaScript/React داخل خدمة Builder منفصلة عن Backend.
- منع Node/npm من الدخول إلى صورة Backend.
- تشغيل build عبر Builder معزول مع bubblewrap وتعطيل الشبكة أثناء خطوة build.
- إخراج artifact محدود الحجم والملفات، مع رفض symlinks ومسارات ZIP غير الآمنة.
- نشر artifact كملفات منفصلة تحت مسار مشروع محدد بدل تنفيذ ZIP داخل Backend.
- توكن معاينة موقّع ومؤقت ومقيد بالمشروع وartifact.
- تقديم ملفات المعاينة عبر مسار مخصص مع CSP وsandbox وconnect-src 'none'.
- عرض المعاينة التنفيذية داخل iframe sandbox="allow-scripts" بدون allow-same-origin.
- الحفاظ على المعاينة الثابتة السابقة باستخدام sandbox="".
- إضافة اختبارات أمنية لمسارات ZIP، توكن المعاينة، CSP، عزل workspace، ونشر artifact.
- عدم تشغيل artifact أو JavaScript المشروع داخل خدمة Backend نفسها.

### تحقق F3.3 النهائي — 2026-10-02
- PR #362: **Merged** — أساس preview-plan.
- PR #363: **Merged** — عقد Builder المعزول.
- PR #364: **Merged** — خدمة Preview Builder مستقلة.
- PR #365: **Merged** — ربط نتائج build بواجهة ProjectEditor.
- PR #366: **Merged** — Secure Preview Origin/CSP/artifact serving.
- CI #3924 على commit c6be6165611b8380849dab2901f39b2f0a505637: **نجح بالكامل** — Backend، Frontend، SDK، Production Compose، Preview Builder.
- CodeQL #623: **نجح**.
- Production Smoke #171: **نجح** بعد الدمج.
- Publish backend image #355: **نجح** بعد الدمج.
- لم تتم إضافة أو ترقية أي موارد Render مدفوعة ضمن F3.3.

### F4 — Project Collaboration / Import-Export Improvements
الحالة: **مكتملة ومتحققة — F4.1 وF4.2 وF4.3 على `main`**

#### F4.1 — Project Collaboration / Membership: **مكتمل ومتحقق**
- أضيفت عضوية المشروع بأدوار `viewer` و`editor` و`manager`.
- أضيفت فحوصات موحدة للوصول إلى المشروع والقراءة والتعديل وإدارة الأعضاء.
- تمت حماية Project Files وProject Memories وChat وسياق المحادثات المرتبط بالمشروع من الوصول بعد سحب العضوية.
- أضيفت اختبارات للعزل بين المستخدمين ومساحات العمل، وصلاحيات viewer/editor/manager، وسحب الوصول.
- migration: `0074_project_collaboration`.
- PR #368 تم دمجه بنجاح.
- merge commit: `325fab92b8e0f6f7fcbbab4cba4e764748fe4976`.

#### F4.2 — Project Import / Export: **مكتمل ومتحقق**
- أضيف archive ZIP canonical بإصدار schema واضح للـmetadata والملفات والذكريات.
- تمت إضافة validation صارمة للحجم، عدد الملفات، المسارات، UTF-8، checksums، والملفات غير المعلنة.
- الاستيراد يدعم fail-by-default عند تعارض الاسم و`rename` صريحًا دون overwrite.
- تم تسجيل نجاح الاستيراد في audit log.
- أضيفت واجهات Frontend لتصدير المشروع واستيراده، مع معالجة تعارض الاسم.
- تم الحفاظ على فحوصات project access وعزل المحادثات حسب المشروع.
- PR #370 تم دمجه بنجاح.
- CI #4008: **نجح بالكامل** — Backend، Frontend، SDK، Production Compose، Preview Builder.
- CodeQL #645: **نجح بالكامل** لـPython وJavaScript/TypeScript.
- merge commit: `a12ee1a863640fbcb9bbdff3ed8a72c4a0de40eb`.
- لم تتم إضافة أو ترقية أي موارد Render مدفوعة ضمن F4.

#### F4.3 — Artifact Management / Conflict Improvements: **مكتمل ومتحقق**
- تم حفظ lifecycle metadata للـproject preview artifacts داخل PostgreSQL.
- أصبحت artifacts السابقة تُعلَّم `superseded` عند نشر artifact أحدث.
- تم رفض duplicate normalized ZIP paths أثناء نشر artifact.
- أصبح عرض preview artifact يتطلب artifact مسجلًا وحالته `active` وضمن مدة الصلاحية.
- أضيفت مسارات project-scoped لعرض وحذف artifacts مع فحوص ownership/membership.
- تمت إضافة تنظيف ملفات artifacts عند الاستبدال وحذف المشروع.
- أضيفت اختبارات lifecycle والعزل والتعارض.
- migration: `0075_project_preview_artifacts`.
- PR #374 تم دمجه بنجاح.
- PR #378 أضاف انتهاء صلاحية artifacts بحالة `expired` وتنظيفًا opportunistic للتخزين، وشدّد عزل تاريخ artifacts، وفرض uniqueness غير حساسة لحالة الأحرف لأسماء المشاريع داخل الـWorkspace.
- CI #4040: **نجح بالكامل** لـPR #374.
- CodeQL #653: **نجح بالكامل** لـPR #374.
- CI #4080: **نجح بالكامل** لـPR #378.
- CodeQL #659: **نجح بالكامل** لـPR #378.
- merge commit لPR #378: `952f7c9aa0991fca7d03a46eec81b4ea67920fac`.
- لا توجد موارد مدفوعة جديدة ضمن F4.

#### إصلاح سلسلة Alembic بعد F4/F5.1: **مكتمل ومتحقق**
- نتج رأسان مستقلان على `0075_project_preview_artifacts`: `0076_project_name_conflict_index` و`0076_agent_workflow_checkpoints`.
- أضيف merge migration `0077_merge_f4_f5_heads` لدمج الرأسين دون تغيير schema إضافي.
- PR #385 تم دمجه بنجاح.
- CI #4134: **نجح بالكامل**.
- CodeQL #671: **نجح بالكامل**.
- merge commit: `cde7d3c4c0045d36c15efd532e614e4a8b33cfc4`.
- بعد الإصلاح أصبح `alembic upgrade head` يصل إلى head واحد في CI.

#### التحقق التشغيلي بعد F4
- لا نعتبر F4 مرادفًا لـProduction-ready؛ يبقى Production Smoke على Render Free نقطة تحقق تشغيلية مستقلة.
- Production Smoke #174 سبق أن سجل timeout متكررًا في `/health` مع نجاح `/ready` وباقي الفحوص، بينما كان التشغيل #173 ناجحًا.

## قاعدة العمل بعد F4
**F4 مغلقة بالكامل.** لا توجد بنود F4 متبقية.

### F5 — Advanced Agent Project Workflows

#### F5.1 — Multi-step Agent Workflow Checkpoints: **مكتمل ومتحقق**
- تم دعم workflow منظم داخل AgentJob بحد أقصى 6 خطوات.
- الخطوات تُنفّذ بالتتابع عبر AgentRuntime الحالي.
- يتم حفظ حالة كل خطوة، عدد المحاولات، run ID، النتيجة، وcheckpoint metadata.
- الخطوات المكتملة تبقى محفوظة عبر الإعادة، ويمكن استئناف المهمة من أول خطوة غير مكتملة.
- الحد الأقصى لمحاولات الخطوة 3 محاولات، مع الحفاظ على توافق إنشاء AgentJob التقليدي.
- أضيفت اختبارات للعزل، checkpoints، resume، وحالات الفشل.
- PR #379 تم دمجه بنجاح.
- CI #4096: **نجح بالكامل**.
- CodeQL #662: **نجح بالكامل** لـPython وJavaScript/TypeScript.
- merge commit: `1c0cb1efeb9ef78a36bbb68e01cdeaf1c47e5385`.
- PR #382 أُغلق لأنه نسخة مكررة من F5.1 بعد دمج #379.

#### F5.2 — Verification / Retry Enhancements: **مكتمل ومتحقق — 2026-10-02**
- أضيفت مرحلة تحقق مستقلة قبل اعتبار خطوة Agent ناجحة.
- أضيفت حالات checkpoint إضافية: `executing` و`verifying` و`retrying` و`step_completed` و`completed` و`failed` و`cancelled`.
- أضيفت bounded retries مع الحفاظ على cumulative input/output token usage.
- تم كشف `workflow_phase` و`retry_count` و`max_retries` و`checkpoint` و`checkpoint_at` داخل AgentJob API.
- تم منع إعادة المحاولة عند التوقف الأمني، مع إعادة تطبيق فحوصات quota وcost budget قبل كل retry.
- migration: `0078_agent_verify_retry`.
- اختبارات regression تغطي retry بعد فشل التحقق ومنع retry بعد security stop.
- PR #387 تم دمجه بنجاح.
- CI #37047362318: **نجح بالكامل** — Backend، Frontend، SDK، Production Compose، Preview Builder.
- CodeQL #37047368789: **نجح**.
- merge commit: `a2d0d7a2dd6d6da124cb7db8834bd8d1d4720780`.
- تم إغلاق PR #381 القديم لأنه أصبح تنفيذًا متجاوزًا بعد اكتمال F5.1 واعتماد تنفيذ F5.2 الجديد.
- لا توجد موارد بنية تحتية جديدة مطلوبة؛ يعتمد التنفيذ على PostgreSQL/Celery/Redis الموجودة.

## F5.3 — Agent Job Lifecycle Control: **مكتمل ومتحقق — 2026-10-02**

- أضيفت حالة persistent باسم `pause_requested` إلى `AgentJob`.
- أضيفت حالة lifecycle جديدة `paused` مع إيقاف تعاوني عند نقاط checkpoint/event الآمنة، دون قتل تنفيذ المزوّد الجاري.
- يمكن إيقاف المهمة وهي `queued` أو أثناء التنفيذ، ثم استئنافها من checkpoint الموجود مع الحفاظ على attempt/retry semantics الخاصة بـF5.1 وF5.2.
- يمكن إلغاء المهمة وهي `paused` مباشرة، وتبقى حالات الـworkflow والـcheckpoint متسقة.
- تم كشف حالة الإيقاف داخل AgentJob API وإضافة endpoints للإيقاف والاستئناف.
- migration: `0079_agent_pause`.
- PR #388 تم دمجه بنجاح.
- commit الدمج بعد squash: `f165c4944ff9c90345947be60f5d40d046381456`.
- CI على آخر commit `da9c26006ea204320dfda5a2df8f9a4686fb3cb2`: **نجح بالكامل** — Backend، Frontend، SDK، Production Compose، Preview Builder.
- CodeQL على آخر commit: **نجح**.
- لا توجد موارد بنية تحتية جديدة أو موارد مدفوعة مطلوبة لـF5.3.

## قاعدة العمل بعد F5.3

F5.1 وF5.2 وF5.3 مغلقة ومتحققة على `main`.
لا توجد حاليًا مواصفة سابقة محفوظة داخل المستودع لمرحلة G، لذلك لا ننسب لها متطلبات تاريخية غير موثقة.
لأغراض الإغلاق العملي للمشروع، يتم تعريف G التالية كمرحلة **Final Productization & Production Acceptance**، وتُنفذ فقط عبر PRs مستقلة وCI/CodeQL والتحقق التشغيلي.

### المرحلة G — Final Productization & Production Acceptance

#### حالة التقدم — 2026-10-02

- **G1 — UI / Mobile Acceptance: مغلقة على مستوى الكود والتحقق الآلي.**
  - تم دمج PR #390.
  - قائمة إجراءات المحادثة في رأس الصفحة أصبحت سياقية ولا تظهر عندما لا توجد إجراءات متاحة.
  - اختبارات Frontend وCI وProduction Smoke بعد الدمج نجحت.
  - يبقى التحقق اليدوي على جهاز هاتف فعلي جزءًا من الإغلاق النهائي الشامل.

- **G2 — Agent / Project End-to-End Acceptance: مكتملة ومتحققة — 2026-10-03.**
  - PR #391 تم دمجه بالـcommit `51cb1bb80ee02878941a9941be5e17c1bea3c475`.
  - أضيف Dockerfile مستقل لنشر Preview Builder، وتم الحفاظ على عزل bubblewrap ومنع الشبكة أثناء build.
  - خدمة Render باسم `ai-chat-preview-builder` تعمل على خطة **Free** وأصبحت `live`.
  - تم إنشاء secret قوي داخل Render للخدمة `ai-chat-preview-builder`، ثم ضبط `PREVIEW_BUILDER_URL=https://ai-chat-preview-builder.onrender.com` و`PREVIEW_BUILDER_TOKEN` في خدمة Backend بالقيمة السرية نفسها، مع إبقاء بقية المتغيرات دون تغيير.
  - تم حفظ إعدادات الخدمتين وإعادة النشر، ثم أكدت سجلات Render أن Builder أصبح `live` وأن Backend استقر ويعيد `/health = 200`.
  - تم إجراء اختبار المشروع والمعاينة فعليًا من المستخدم، وبذلك أُغلقت متطلبات G2 الحالية.

- **G3 — Security / Reliability / Cost Acceptance: مغلقة ومتحققة — 2026-10-06.**
  - في Supabase `ai-chat-prod-db` تم التحقق مباشرة من أن جميع **46/46** جدولًا في schema `public` لديها RLS مفعّل، ولا يوجد أي جدول عام بدون RLS.
  - Migration `0080_harden_public_rls` فعّلت RLS على الجداول الحساسة الـ12 التي كانت خارج الحماية سابقًا: `agent_jobs`, `agent_workflow_steps`, `oauth_connections`, `oauth_states`, `project_files`, `project_members`, `project_preview_artifacts`, `saved_prompt_versions`, `webhook_deliveries`, `webhook_endpoints`, `workspace_rbac_permissions`, `workspace_rbac_roles`.
  - تم التحقق من أن هذه الجداول الـ12 لا تمنح `anon` أو `authenticated` أي صلاحيات جدول مباشرة؛ والمنح الموجودة في بقية الجداول محكومة بـRLS مع عدم وجود سياسات، ما يجعل الوصول المباشر عبر Data API **default-deny**.
  - راجعنا نموذج الوصول الفعلي: التطبيق لا يعتمد على Supabase client في الواجهة، والوصول التشغيلي يتم عبر Backend FastAPI/PostgreSQL المباشر، لذلك **لم نضف سياسات RLS تخمينية** مثل `auth.uid()` قد لا تطابق نموذج الصلاحيات الفعلي.
  - Security Advisor يسجل **46 ملاحظة INFO** من نوع `rls_enabled_no_policy`، وهي متسقة مع هذا التصميم، وتحذيرًا واحدًا `extension_in_public` للامتداد `vector`. تم الإبقاء على `vector` في `public` عمدًا لأن نقله قد يغير موضع نوع `vector(768)` المستخدم في RAG ويحتاج نافذة تغيير منفصلة؛ لا يُعتبر مانعًا وظيفيًا للإغلاق الحالي.
  - Deploy Backend للـcommit `6063adebae906f907148acda77995a78a24f2716` أصبح **live** على Render Free، وPublish Backend Image نجح.
  - PR #399 أصلح ترتيب Production Smoke ليبدأ بـ`/ready` قبل `/health`، ثم نجحت CI وCodeQL، وتم دمجه في `main`.
  - PR #400 وثّق المراجعة الأمنية، ونجحت CI وCodeQL، ثم تم دمجه في `main`.
  - **G3 مغلقة رسميًا.**

- **G4 — Production Acceptance: مغلقة ومتحققة — 2026-10-05.**
  - تم إصلاح تشغيل Backend ليحترم `PORT` الخاص بـRender، وأصبح deploy الإصلاح `live`.
  - تم التحقق من أن قاعدة الإنتاج الحقيقية هي Supabase `ai-chat-prod-db` في `us-east-2`.
  - تم إنشاء fixture حقيقي للإنتاج باسم **G4 Production Editor Smoke**، Project ID = `1`، في workspace `2`، ويحتوي `index.html`.
  - تم نشر مدخل مباشر إلى Project Editor داخل صف المشروع، مع إبقاء صلاحية التعديل مقيدة بمالك المشروع أو `owner/admin`.
  - تم تنفيذ قبول G4 يدويًا من واجهة الإنتاج على الهاتف.
  - تم التحقق من فتح **Project Editor** للمشروع، وظهور **Project Files** و`index.html`.
  - تم التحقق من **Preview Plan** وظهور الاستراتيجية `static-html` والحالة `ready`.
  - تم التحقق من **Validate** والنتيجة `0 errors, 0 warnings` لملف المشروع.
  - تم التحقق من **Safe Preview** بنجاح.
  - اختبارات CI الآلية الخاصة بـProjectEditor تغطي أيضًا preview وpreview-plan وpreview-build، وآخر CI عام نجح بالكامل.
  - لم يتم استخدام خدمة المتصفح المدفوعة في الإغلاق النهائي؛ تم الاعتماد على التحقق اليدوي المجاني واختبارات CI.
  - **G4 مغلقة.**

- **G5 — Release & Closure: قيد التنفيذ — 2026-10-06.**
  - G1 وG2 وG3 وG4 مغلقة ومتحققة.
  - تم تثبيت آخر `main` على commit `f014812b68ee421f77e170af26ee567c20bdb0e3` بعد دمج توثيق G3.
  - تم تنفيذ تحسين Production Smoke ودمجه في `main`.
  - تم التحقق من CI وCodeQL على آخر سلسلة تغييرات قبل الإغلاق.
  - **المتبقي الوحيد:** إنشاء release/tag النهائيين وتوثيق رقم الإصدار/الـartifact النهائي. لا يتم اختراع tag تلقائيًا لأن اتصال GitHub الحالي يوفر قراءة وإدارة PR/branches ولا يوفّر عملية إنشاء Release/Tag مباشرة.
  
### ترتيب التنفيذ الحالي بعد G4 — 2026-10-06

1. G3 — **مغلقة رسميًا**.
2. G5 — **جارٍ إغلاقها** عبر release/tag النهائي وقائمة الإغلاق النهائية.

