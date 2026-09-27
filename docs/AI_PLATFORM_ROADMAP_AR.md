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

الحالة: **قيد التنفيذ — D1 وD2 وD3 وD4 مكتملة ومتحققة**

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
- تمت إضافة allowlist عامة لأدوات Agent عبر `AGENT_ALLOWED_TOOLS_JSON`، وتُطبّق قبل تعريف الأدوات المعروضة للنموذج.
- أصبح `ToolRegistry` يفرض allowlist صريحة عند تسجيل الأدوات، مع إمكانية التحقق من السماح قبل التنفيذ/الاكتشاف.
- أدوات MCP لا تُكشف تلقائيًا: كل خادم يجب أن يحدد `allowed_tools` بأسماء الأدوات البعيدة الموثوقة.
- تستمر قيود MCP السابقة: التكامل مغلق افتراضيًا، وحدود الخوادم والأدوات، وHTTPS في production.
- تمت إضافة اختبارات للـRegistry، وAgent Runtime، واكتشاف MCP وتنفيذ الأدوات المسموحة ورفض الأدوات غير المسموحة.
- PR #308 تم دمجه بنجاح.
- CI run `3126`: **نجح**.
- CodeQL run `356`: **نجح**.
- commit الدمج بعد squash: `82f4e295c1c8fe064fef91131adaee17d87a19bf`.


1. Tool Registry
2. MCP integration
3. Agent runtime
4. Tool permissions
5. Sandboxed code execution
6. Long-running agent jobs
7. Scheduled agents
8. Prompt-injection / tool-abuse defenses

## المرحلة E — Platform & Developer Ecosystem

الحالة: **لم تبدأ**

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
