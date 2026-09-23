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

بعد دمج PR #201:

- PRs #190–#201 تمت مراجعتها من ناحية التكرار.
- #201 دمج بنجاح.
- إصلاح image-RAG fallback أصبح في `main`.
- #200 مغلق باعتباره نسخة أقدم من نفس الإصلاح.
- CI وCodeQL نجحا لنسخة #201.
- البنية الحالية على Render ما زالت تحتاج إكمال عناصر Production Foundation، خصوصًا Health Check وCelery Worker/Beat والتخزين والنسخ الاحتياطية والإعدادات الإنتاجية.

## قاعدة المتابعة

عند بدء أي جلسة عمل جديدة، نبدأ من آخر حالة مؤكدة في هذه الوثيقة وGitHub `main`، ثم نكمل أول بند غير مكتمل في المرحلة الحالية قبل الانتقال إلى ميزات جديدة.
