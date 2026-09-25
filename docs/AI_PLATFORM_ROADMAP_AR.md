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

- Health Check: **غير متحقق على خدمة Render الحالية** — الكود يحتوي على `/health` و`render.yaml` يحدد `healthCheckPath: /health`، لكن فحص Render للخدمة الحالية `ai-chat-backend` أظهر أن إعداد Health Check الفعلي فارغ.
- Celery Worker: **غير موجود كخدمة Render مستقلة حاليًا، لكن التشغيل المضمّن داخل `ai-chat-backend` مُثبت من السجلات** — ظهرت مهام Celery مستلمة ومنفذة بنجاح كل دقيقة.
- Celery Beat: **غير موجود كخدمة Render مستقلة حاليًا، لكن التشغيل المضمّن داخل `ai-chat-backend` مُثبت من السجلات** — ظهرت رسائل Scheduler وإرسال المهام المجدولة بصورة متكررة.
- PostgreSQL production setup: **غير مكتمل** — خدمة قاعدة البيانات الإنتاجية المعرفة في `render.yaml` ليست ضمن الخدمات الحالية المتحققة في Render.
- Redis production setup: **غير مكتمل** — خدمة Redis المعرفة في `render.yaml` ليست ضمن الخدمات الحالية المتحققة في Render.
- Object Storage: **مكتمل ومتحقق إنتاجيًا** — Render أثبت الاتصال، ثم نجح اختبار upload → read → delete على Backblaze B2.
- Off-site backups: **قيد الإكمال** — Workflow يستخدم أسرار `B2_*` الصحيحة، لكن `PRODUCTION_DATABASE_URL` غير موجود حاليًا في GitHub Actions، ولم تُثبت نسخة احتياطية ناجحة بعد.
- Domain + HTTPS: **غير مكتمل**.
- Production smoke tests/E2E: **Workflow موجود؛ تشغيل إنتاجي ناجح لم يُثبت في بيئة GitHub Actions بعد**.

### تحقق Render الفعلي — 2026-09-25

تم اختيار مساحة Render الصحيحة: `My Workspace` (`tea-dagsi5ou01pc73f2g470`).

الخدمات الفعلية التي ظهرت في Render:
- `ai-chat-backend` — Web Service، الخطة الحالية **Free**، والرابط `https://ai-chat-backend-ltxa.onrender.com`، وHealth Check Path الفعلي **فارغ**.
- `ai-chat-frontend` — Static Site، والرابط `https://ai-chat-frontend-v8ma.onrender.com`.

الخدمات المعرفة في `render.yaml` ولكنها لم تظهر ضمن قائمة الخدمات الحالية التي تم التحقق منها:
- `ai-chat-worker`
- `ai-chat-beat`
- `ai-chat-redis`
- `ai-chat-db`

هذا الفرق يعني أن ملف `render.yaml` يمثل البنية الإنتاجية المستهدفة، لكنه لم يُطبَّق بالكامل على Workspace الحالي.

## المرحلة B — Reliability & Observability

الحالة: **لم تبدأ**

1. OpenTelemetry / distributed tracing
2. Alerts
3. Retry / timeout / circuit breaker
4. Job system موحد
5. فصل Database migrations عن تشغيل replicas
6. Database optimization
7. Restore drills
8. SLO/error-budget monitoring

## المرحلة C — Advanced AI

الحالة: **لم تبدأ**

1. Model Router
2. Hybrid RAG
3. Reranking
4. Citations
5. Advanced memory
6. Evaluation framework
7. AI cost controls

## المرحلة D — Agent Platform

الحالة: **لم تبدأ**

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

## متطلبات إغلاق كل مرحلة

لا تُعلن المرحلة مكتملة إلا بعد:

- نجاح الاختبارات الآلية ذات الصلة.
- مراجعة التغييرات وعدم وجود تكرار معروف.
- التحقق من المسار الإنتاجي المتأثر.
- تحديث الوثائق.
- تسجيل النتيجة في هذه الخارطة.
- التأكد أن التغييرات لا تكسر المراحل السابقة.

## الوضع الحالي المعروف

بعد مسار Production Foundation الحالي:

- PRs #190–#230 تمت مراجعتها من ناحية التكرار ضمن مسار Production Foundation.
- #201 دمج بنجاح، وإصلاح image-RAG fallback أصبح في `main`.
- #212 أضاف Production smoke workflow يدويًا ويوميًا.
- #213 أضاف Workflow للنسخ الاحتياطي الخارجي PostgreSQL، مع تفعيل محمي بمتغير Repository حتى تتم إضافة التخزين والأسرار.
- #215 شدّد تكامل Object Storage: لا يُفعّل remote storage إلا عند اكتمال الإعداد، أُضيف توقيع SigV4 وفحص bucket واختبارات تغطية.
- Render يعمل حاليًا بخيار Celery المضمّن المجاني، وتم التحقق مباشرةً في السجلات الحالية من Worker وBeat أثناء التشغيل.
- Object Storage أصبح مفعّلًا على Render ومتحققًا باختبار فعلي upload/read/delete على B2.
- Off-site PostgreSQL backup أصبح جاهزًا كـ Workflow، وتمت محاكاة التشغيل الفعلي حتى نقطة التحقق من الأسرار؛ النتيجة أثبتت أن `PRODUCTION_DATABASE_URL` ما زال مفقودًا من GitHub Actions. بعد إضافته وتفعيل `PRODUCTION_BACKUP_ENABLED=true` يجب تشغيل نسخة ناجحة قبل الإغلاق.
- Health Check داخل `render.yaml` مضبوط على `/health`، لكن تحقق Render الحالي أظهر أن الخدمة الفعلية لا تحتوي Health Check Path بعد، ولم تظهر سجلات HTTP لـ`/health` أثناء الفحص.
- التحقق الخارجي الحالي لـ`https://ai-chat-backend-ltxa.onrender.com/health` أعاد HTTP 200 مع `status=ok` و`database=ok`، و`/billing/plans` أعاد HTTP 200 مع خطتين. هذا يثبت صحة endpoint لكنه لا يغلق إعداد Health Check الداخلي في Render.
- PostgreSQL وRedis الحاليان المستهدفان في `render.yaml` ما زالا بحاجة إلى تطبيق/تحقق فعلي على Render؛ الخدمات الحالية المتحققة لا تتضمنهما.
- Smoke/واجهة الإنتاج: الصفحة الرئيسية للواجهة أعادت HTTP 200، لكن `/pricing` أعاد HTTP 404. السبب أن الواجهة SPA تعتمد على `window.location.pathname` بينما Static Site الحالي لا يملك rewrite fallback.
- تم إصلاح مصدر الحقيقة في `render.yaml` بإضافة rewrite من `/*` إلى `/index.html` في خدمة `ai-chat-frontend` (commit `8776af23d7a900a66b1e5a043c7f15db0846c5f3`). لكن هذا الملف خارج `ai-frontend`، والخدمة الحالية لم تُحدّث بهذه القاعدة؛ لذلك بقي الاختبار الحي لـ`/pricing` على 404 حتى تتم مزامنة Blueprint أو تعديل Routes من إعدادات Render.
- إصلاح SQLAlchemy/PostgreSQL الخاص بـAnalytics تم دمجه في commit `edf32e14cb76413a3ec7abc0831cdf2c468af716`.
- دورة CI على `edf32e14...` نجحت بالكامل: CI، Backend pytest، Frontend، وProduction Compose.
- CodeQL وPublish backend image على نفس الـcommit نجحا أيضًا.
- أحدث Deploy للـBackend على Render أصبح `live` على `edf32e14...`.

### آخر تحقق تشغيلي — 2026-09-25

- آخر Deploy حي للـBackend كان بحالة `live` على Render.
- سجلات التطبيق أظهرت `run_due_scheduled_tasks` مستلمة ومنفذة بنجاح، مع Scheduler يرسل المهمة بصورة دورية.
- لم تظهر سجلات من نوع `request` لمسار `/health` أثناء نافذة التحقق؛ لذلك لم يتم إغلاق بند Health Check.
- النتيجة النهائية لدورة CI رقم `36164812684`: **success**.
- CodeQL رقم `36164812643`: **success**.
- Publish backend image رقم `36164812677`: **success**.

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main`، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.
