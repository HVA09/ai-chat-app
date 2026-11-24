# Upload Processing Worker — Design Gate (PR #767)

Status: design only. This document does not enable a worker, broker consumer, scheduler, migration, deployment, or cleanup process.

## Current verified baseline

- Durable jobs use the `extract` and `index` stages, keyed by `(lease_id, stage, stage_revision)`.
- Dispatch is at-least-once. Duplicate broker messages are expected and must be harmless.
- Job claim/heartbeat/completion use a generation plus a hashed owner token.
- Job state helpers acquire locks in `User -> UploadLease -> UploadProcessingJob` order.
- A processing lease expiry is advisory. It is not proof that the previous process stopped and must never authorize reclaim or deletion.
- CI on commit `abb5c4fe67700f3234441d18e3443161cd3bfee3` passed: 728 backend tests, including the PostgreSQL concurrent-dispatcher test; frontend, SDK, production-compose, preview-builder and CodeQL passed.

## Existing upload path that must be preserved during the transition

`app/routers/files.py` currently receives and validates the upload, writes it to storage, claims the upload lease, extracts text synchronously, creates the `FileAttachment`, finalizes the lease, and may prepare/persist the RAG index in the request. It contains account-deletion serialization and cleanup-intent safeguards.

The durable job model is not yet wired into this request path. Do not create jobs in parallel with the current synchronous extraction/indexing path: that would duplicate work and introduce competing ownership of the same attachment.

## Worker contract

1. A broker message carries only the durable `job_id`; it is never trusted as authorization.
2. The worker opens a short DB transaction and claims the job with `claim_upload_processing_job`. Commit the claim before external I/O. A duplicate delivery that cannot claim exits successfully without processing.
3. Load the committed lease and attachment using the lease relationship. Require a live user owner, expected attachment ID, and valid object metadata. Never infer object ownership from a broker payload.
4. Do not hold a DB connection or row lock while downloading/materializing an object, extracting text, or calling an embedding provider.
5. Before any persisted stage result, open a fresh transaction, revalidate the owner and job generation/token through the state helpers, lock the attachment row, and verify it still belongs to the same lease/user and expected source fingerprint.
6. Persist the stage result and mark the job succeeded in the same transaction. If the fencing check fails, discard the result; a stale worker must not overwrite newer work.
7. Heartbeats use fresh short transactions and the same fencing credentials. A failed heartbeat means stop before any further write. Do not treat cancellation or timeout alone as proof that an external storage/provider operation has stopped.
8. Classify transient provider/storage failures into bounded retry delays; sanitize persisted error codes. Permanent validation/unsupported-file failures become terminal. Never persist raw exception text, secrets, or file contents in job error fields.
9. Indexing must prepare embeddings outside the write transaction, then atomically replace chunks using `persist_file_index` after rechecking the source fingerprint and job fence.
10. No automatic lease reclaim, object deletion, local-file deletion, expiry-based cleanup, or production activation is part of this worker phase.

## Stage boundaries

### Extract
- Materialize only the object referenced by the committed lease/attachment.
- Use the existing bounded `extract_text` implementation and its supported MIME allowlist.
- Persist `FileAttachment.extracted_text` only after rechecking the job fence and attachment identity.
- Unsupported binary/image inputs produce a deliberate no-text outcome; image vision processing remains a separate explicit workflow.

### Index
- Read the committed extracted text and capture its normalized fingerprint.
- Call `prepare_file_index` outside a DB transaction.
- Revalidate the fingerprint and job fence, then call `persist_file_index` and complete the job atomically.
- Provider failure must preserve the previous index.

## Required tests before any runtime wiring

- Duplicate delivery: exactly one claim proceeds; all others no-op.
- Stale generation/token cannot heartbeat, persist, retry, or complete.
- User deletion during extraction/provider I/O prevents subsequent writes.
- Missing/orphaned lease or attachment fails closed without storage mutation.
- Extraction success, empty/unsupported content, malformed document, and bounded-size behavior.
- Embedding failure preserves existing chunks and index metadata.
- Source mutation between preparation and persistence is rejected.
- Heartbeat failure stops before a later persistence attempt.
- Transaction rollback leaves the job retryable and does not publish a false success.
- PostgreSQL integration tests cover lock order and concurrent claim/completion.

## Activation gate

Only after the worker service and tests pass may a later isolated change add a broker consumer and connect job creation to upload finalization. Keep the existing synchronous path intact until that later cutover is separately tested. Any production migration, worker deployment, broker activation, object-storage mutation, or cleanup automation requires a separate explicit review and is outside this PR's current scope.

## بوابة تنفيذ مشرف محلّل الملفات (Parser Supervisor)

هذه البوابة إلزامية قبل ربط عامل الاستخراج بأي وسيط رسائل أو تغيير مسار الرفع المتزامن. حدود الصفحات والصفوف وعدد الأحرف في المحلّل الحالي تقلل حجم المخرجات والاجتياز، لكنها **لا تضمن** حدًا صارمًا للذاكرة أو زمن CPU؛ كما أن مكتبات PDF وDOCX قد تقرأ أو تفك ضغط أجزاء كبيرة قبل تطبيق الحدود.

### عقد العملية الأم والطفل

1. تبقى قراءة قاعدة البيانات، امتلاك job والـ lease، تجديد heartbeat، جلب الملف من التخزين، والتحقق النهائي والحفظ ضمن العملية الأم فقط.
2. تُشغّل عملية التحليل باستخدام سياق `spawn` مستقل، لا `fork` لعملية تحتوي اتصالات SQLAlchemy أو Celery. لا تمرر إلى الطفل كائن Session أو ORM أو إعدادات أسرار أو owner token أو صلاحيات تخزين/كتابة.
3. لا يستقبل الطفل إلا مسارًا محليًا للقراءة فقط، ونوع MIME تم التحقق منه، وخيارات تحليل محدودة. يجب أن تكون دالة التشغيل على مستوى الوحدة وقابلة للتسلسل، وأن يكون بدء الطفل واختباره مستقلًا عن بدء التطبيق.
4. يكون اتصال النتائج محدود الحجم صراحةً، ويُرفض أي payload يتجاوز سقف الأحرف/البايتات قبل فكّه أو تحويله إلى كائنات كبيرة. لا يُسمح للطفل بكتابة النتيجة مباشرة إلى قاعدة البيانات أو تخزين الكائنات.
5. تستخدم العملية الأم ساعة رتيبة `time.monotonic()` لاحتساب مهلة التحليل. تجدد heartbeat في معاملات قصيرة مستقلة أثناء الانتظار؛ ولا تحتفظ باتصال أو قفل قاعدة بيانات طوال التحليل.
6. عند انتهاء المهلة أو الإلغاء: تطلب الأم الإنهاء، تنتظر فترة سماح محدودة، ثم تفرض القتل إذا لزم. بعدها تنفذ `join/wait` وتتحقق من أن العملية لم تعد حية وأن حالة خروجها معروفة.
7. لا يكفي إرسال terminate/kill أو انتهاء المهلة أو lease لإثبات التوقف. إذا تعذر إثبات خروج الطفل وإعادة جمعه، تفشل الأم مغلقًا: لا حفظ للنص، لا إكمال للـ job، لا reclaim للجيل، ولا حذف للمصدر أو مجلد العمل المؤقت.
8. لا يُحذف مجلد العمل أو المصدر المؤقت إلا بعد إثبات توقف الطفل. إذا ماتت العملية الأم أو تعطل المضيف، يجب أن يثبت تصميم التشغيل أن الأطفال لا يواصلون العمل خارج نطاق إشراف قابل للإنهاء؛ وإلا تبقى إعادة المطالبة والتنظيف معطّلين. يجب اختبار هذا السلوك على بيئة التشغيل المستهدفة، لا افتراضه من سلوك `multiprocessing` وحده.
9. بعد نتيجة ناجحة وخروج الطفل، تعيد الأم التحقق من heartbeat والجيل والرمز وملكية المرفق وبصمة المصدر في معاملة جديدة قبل الحفظ الذري. فشل أي تحقق يعني إسقاط النتيجة دون كتابة.

### حدود الموارد المطلوبة

- سقف بايتات الملف قبل التحليل، مع حد مستقل لحجم فك ضغط الأرشيف/محتوياته، وليس الاعتماد على حجم الملف المضغوط وحده.
- سقف للذاكرة وCPU والوقت للعملية الفرعية، مفروض من نظام التشغيل/الحاوية حيثما أمكن؛ حدود مكتبة التحليل وحدها ليست بديلًا.
- حدود مستقلة للصفحات، الأوراق، الصفوف، الأعمدة، الخلايا، الفقرات، صفوف الجداول، ومخرجات النص.
- مجلد مؤقت خاص بالمهمة وصلاحيات قراءة فقط للمصدر داخل الطفل، دون مشاركة مجلدات بين مهام متزامنة.
- قناة IPC محدودة ومتحقق من نوع رسائلها وحجمها، مع إغلاقها وجمع العملية في جميع مسارات النجاح والفشل.

### اختبارات قبول إلزامية قبل أي تفعيل

- نجاح التحليل يعيد نصًا لا يتجاوز الحد، ثم يثبت خروج الطفل قبل الحفظ.
- timeout يمر بمراحل terminate ثم kill ثم join، ولا تُقبل النتيجة المتأخرة.
- heartbeat يفشل أثناء التحليل: لا persistence حتى لو أعاد الطفل نتيجة لاحقًا.
- الطفل يتعطل أو يرسل رسالة تالفة/أكبر من الحد: لا حفظ ولا تسريب للـ payload.
- يتعذر إنهاء الطفل أو إثبات خروجه: لا حفظ، ولا reclaim، ولا حذف للمصدر أو temp directory.
- إلغاء المهمة أو موت العملية الأم: لا يبقى طفل يتابع التحليل دون إشراف؛ يُختبر ذلك على نظام التشغيل/الحاوية المستهدفة.
- اختبار ملفات PDF/DOCX/XLSX كبيرة أو مشوهة وأرشيفات عالية نسبة الضغط مع قياس حدود الذاكرة وCPU والوقت.
- تزامن مهام متعددة لا يسبب مشاركة ملفات مؤقتة أو خلط نتائج IPC.
- جميع الاختبارات تستخدم ملفات اختبار وقاعدة بيانات وتخزينًا محليًا/وهميًا؛ لا تستخدم خدمات الإنتاج.

### قرار التنفيذ

لا يُعد هذا التصميم منفذًا بمجرد إضافة الوثيقة أو حدود الاجتياز الحالية. يجب بناء مشرف قابل للاختبار مع اختبارات فعلية لإثبات إنهاء الطفل، وحدود الموارد، ورفض النتائج المتأخرة. وحتى اجتياز ذلك تبقى خدمة العامل غير موصولة، ويبقى مسار الرفع الحالي كما هو، ولا يُفعّل أي dispatcher أو broker consumer أو cleanup.
