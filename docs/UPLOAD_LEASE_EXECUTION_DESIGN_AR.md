# بروتوكول تنفيذ Upload Lease والتنظيف الآمن — تصميم تنفيذي

## الحالة
وثيقة تصميم فقط. لا تضيف migration أو تغيّر سلوك الرفع أو تحذف ملفات. لا يُسمح بتفعيل reconciler قبل اكتمال مراحل التنفيذ والاختبارات المذكورة أدناه.

## نتائج فحص main
- `POST /files/upload` يستقبل الجسم ويكتب ملفاً مؤقتاً محلياً، ثم ينقله إلى المسار النهائي ويرفعه إلى S3 (إن كان مفعلاً)، ثم يستخرج النص، ثم ينشئ `FileAttachment`، ثم ينفذ embeddings بصورة متزامنة.
- القراءة multipart محدودة بالحجم، لكن لا يوجد deadline إجمالي لدورة الطلب.
- `extract_text` يعمل تزامنياً داخل async route؛ timeout للـ coroutine لا يوقف parser متزامناً بدأ بالفعل.
- `embed_documents_sync` يملك HTTP timeout لكل طلب (45 ثانية)؛ عدد الدفعات متغير، ولا يوجد deadline إجمالي لمرحلة الفهرسة.
- Celery موجود في `app/tasks.py` لمهام البريد والمهام المجدولة وAgent jobs وwebhooks. لم نجد مسار file-upload task حالياً ولا task hard/soft time limits مهيأة في التطبيق.
- لذلك لا توجد حالياً ضمانة قابلة للاعتماد لوقت توقف كل الآثار الجانبية.

## القرار المعماري
لا نعتبر heartbeat أو وقت إنشاء الملف وحده دليلاً كافياً لسلامة الحذف. يلزم فصل دورة حياة الرفع إلى مرحلتين واضحتين:
1. HTTP ingress: تحقق الصلاحيات والحصص، أنشئ lease durable قبل إنشاء أي managed object، واستقبل الجسم إلى staging مؤقت محدود الحجم والمدة.
2. Processing worker: claim lease بواسطة fencing token، تحقق النوع، اكتب managed object، استخرج النص، نفّذ indexing، ثم finalize attachment وlease في transaction واحدة.

يجب أن تكون staging location منفصلة عن namespace الذي يفحصه reconciler. يجب ألا يقرأ reconciler staging أو يحذف ملفاتها أثناء احتمال وجود HTTP ingress نشط.

## نموذج UploadLease المقترح
- `id`: UUID عشوائي.
- `user_id`: FK مع سياسة حذف متوافقة مع account deletion.
- `object_key`: managed key متوقع ومحدد من بداية العملية.
- `staging_key` أو staging identity: مسار/مرجع staging معزول، دون السماح بمسار مطلق يقدمه العميل.
- `status`: `receiving | queued | processing | committed | cleanup_pending | failed`.
- `generation`: عدد متزايد fencing generation.
- `owner_token_hash`: تخزين hash/token verifier لا secret خام.
- `heartbeat_at`, `expires_at`, `created_at`, `updated_at`.
- `attachment_id`: nullable FK بعد finalize.
- قيود وفهارس على status, expires_at, user_id, object_key، مع uniqueness تمنع تكرار lease key.

كل انتقال حالة يجب أن يكون conditional compare-and-swap على generation + status + owner token. العامل القديم لا يستطيع heartbeat أو finalize أو delete بعد أن يخسر الملكية.

## حدود الزمن والإلغاء
- إضافة حدود منفصلة ومقاسة لـ ingress، validation/extraction، storage، indexing، وإجمالي worker task.
- worker queue منفصل لمهام الملفات، مع hard task time limit وsoft limit؛ يجب اختبار سلوك worker process عند hard kill فعلياً، وليس الاكتفاء باختبار استثناء Python.
- استخدام worker process معزول لا thread يمكن أن يستمر بعد إلغاء coroutine. أي عملية parsing/embedding لا تملك حد توقف مثبت تمنع منح lease expiry حق الحذف.
- تجديد heartbeat بين مراحل العمل وقبل وبعد كل side effect خارجي.
- فشل heartbeat/CAS يوقف العامل قبل side effect التالي. إذا كان side effect جارياً عند فقد الاتصال، لا يفترض أنه توقف؛ تسجل الحالة uncertain وتنتظر recovery window مرتبطة بحد worker القسري المثبت.
- لا تُشتق expiry من رقم تخميني. تحسب من hard task limit + broker delivery/termination allowance + storage completion/abort bound + safety margin موثق.

## ترتيب التنفيذ والمعاملات
1. migration + model + repository methods للـ lease فقط، مع اختبارات PostgreSQL للـ CAS والتنافس.
2. HTTP ingress: إنشاء lease قبل إنشاء أي managed object، وstaging محدود، وإغلاق/حذف staging محلياً best-effort دون اعتبار ذلك cleanup نهائياً.
3. enqueue task بعد commit للـ lease. فشل enqueue يحول الحالة إلى durable retryable queued/cleanup_pending حسب المرحلة؛ لا تعتمد على رسالة Redis وحدها كمصدر الحقيقة.
4. worker claim بواسطة CAS، ثم heartbeat مرحلي، وفحص generation قبل كل external side effect.
5. بعد اكتمال object + extraction + indexing: transaction واحدة تنشئ/تحدث FileAttachment وتحوّل lease إلى committed وتربط attachment_id.
6. الفشل: سجّل cleanup_pending durable. الحذف المباشر best-effort فقط، ولا تمسح lease قبل إثبات اختفاء كل الآثار.
7. reconciler منفصل، dry-run افتراضياً، bounded batches، persisted pagination/progress، ومراقبة.

## قواعد reconciler
- يفحص فقط managed namespace `users/` ومسار upload المحلي المحدد؛ لا يعمل bucket-wide destructive scan.
- لا يحذف attachment committed ولا object مرتبطاً به.
- لا يحذف lease نشطة، ولا lease غير محسومة، ولا object بmetadata غامضة.
- DB unavailable أو listing failure أو pagination غير مكتملة أو permission error أو generation ambiguity = إيقاف الدفعة دون حذف.
- S3 pagination يجب أن تكتمل بصورة موثقة؛ لا تعامل صفحة جزئية على أنها جرد كامل.
- legacy `object_key IS NULL`: اشتقاق المفتاح من `user_id + stored_filename` مسموح فقط بعد إثبات semantics القديمة وعدم وجود تعارض.
- كل حذف idempotent، bounded، مسجل بمعرف lease دون بيانات حساسة.
- dry-run يجب أن يعرض سبب كل قرار؛ التفعيل يتطلب موافقة مستقلة بعد مراجعة النتائج.

## Account deletion والتزامن
- lease creation يجب أن يتسلسل مع account deletion باستخدام نفس user row lock وترتيب الأقفال المعتمد في #760.
- account deletion لا يتجاهل leases قيد المعالجة؛ يجب أن يوقف إنشاء leases جديدة ويطلب إلغاء/تنظيف leases الحالية بطريقة durable.
- لا يتم حذف المستخدم أو metadata التي يحتاجها reconciler قبل تحويل كل leases إلى حالة recovery durable.
- لا تغير مسار حذف الحساب في #760 ضمن هذه المهمة دون مراجعة مستقلة لتجنب دمج مخاطر مختلفة.

## الاختبارات المطلوبة قبل أي حذف آلي
- lease creation مقابل account deletion باستخدام PostgreSQL concurrency test.
- worker claim/heartbeat/finalize CAS وstale generation rejection.
- slow upload حي لا يحذف ولا تنتهي ملكيته خطأ.
- hard worker kill أثناء upload/extraction/embedding ثم recovery.
- committed attachment لا يحذف حتى مع lease قديمة أو duplicate task.
- double failure: object write succeeds + DB finalize fails + direct delete fails + queue/outbox unavailable؛ reconciler يستعيد لاحقاً.
- S3 pagination partial/failure، local symlink/path traversal، permission errors.
- legacy null object_key mapping.
- retry/duplicate task delivery/idempotency.
- فشل DB/listing أو metadata ambiguity يثبت fail-closed.
- اختبار end-to-end للـ task hard time limit مع worker process حقيقي في CI.

## معايير القبول
- إثبات hard upper bound للعملية بأكملها أو إثبات أن أي worker قديم لم يعد قادراً على إحداث side effect بعد expiry.
- لا يتم استخدام العمر وحده كشرط حذف.
- لا destructive reconcile دون dry-run evidence ومراجعة مستقلة.
- كل CI وCodeQL على exact head ينجحان.
- لا نشر ولا اتصال ببيانات أو تخزين مستضاف أثناء التطوير؛ جميع اختبارات التخزين تستخدم mocks/temp directories/containers معزولة.

## نطاق هذه الوثيقة
تسجل التصميم ونتائج الفحص فقط. لا تعني أن UploadLease أو file worker أو reconciler قد تم تنفيذها.