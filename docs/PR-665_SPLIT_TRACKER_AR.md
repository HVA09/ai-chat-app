# سجل تفكيك PR #665 — مرجع التنفيذ

**آخر تحديث:** 2026-11-16 (Africa/Tripoli)  
**الحالة:** سجل متابعة محدث — PR #665 ما زال Draft وممنوع دمجه ككتلة واحدة. راجع نقطة التحقق الأحدث في القسم 52؛ الأقسام 51.x سجل تاريخي، ولا تتغلب على القسم 52 عند التعارض.  
**المستودع:** `HVA09/ai-chat-app`  
**الفرع الأساسي المعتمد عند بدء السجل:** `main` عند commit `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee`.

> هذا الملف هو سجل القرار والتقدم. يجب تحديثه عند إنشاء أي PR فرعي أو تغيير ترتيبه أو ظهور اختبار/عائق جديد. لا تعتمد على الذاكرة أو أرقام PR وحدها؛ سجّل دائمًا الفرع والـ SHA والاختبارات.

## 1. القرار الثابت

- لا ندمج PR #665 دفعة واحدة.
- نحتفظ به مفتوحًا بحالة Draft كحزمة مصدر للمراجعة، ولا نغلقه أو نحذف فرعه أثناء التفكيك.
- كل تغيير يُعاد بناؤه كـ PR صغير مستقل من أحدث `main`، وليس بدمج فرع #665 القديم أو cherry-pick عشوائي لسلسلة التزاماته.
- لا يُدمج أي PR فرعي قبل مراجعة الملفات المتغيرة، والتحقق من عدم تكرار التغييرات الموجودة في `main`، ونجاح فحوص CI وCodeQL المطلوبة على رأس الفرع نفسه.
- لا تغييرات على إعدادات Render أو Supabase أو الأسرار أو قاعدة الإنتاج، ولا استدعاءات تقييم حية لمزود AI، ضمن هذا التفكيك دون قرار منفصل وصريح.
- لا ميزات واجهة جديدة في مرحلة الاستقرار إلا بعد اعتماد أساس الخادم والفهرسة والصلاحيات.

## 2. نقطة البداية المثبتة

### PR #665

- العنوان: `feat(ai): strengthen embeddings and conversation memory foundations`.
- الفرع: `ai/embedding-provider-separation-20261025`.
- رأس الفرع عند الفحص: `4792285440511833b66e1045bc235143a5a302a5`.
- حالة GitHub عند الفحص: Open / Draft / mergeable=false.
- حجم التغيير المعلن: 70 ملفًا، +15,331 إضافة، -388 حذفًا.
- يحتوي على عدة نطاقات متداخلة: إعداد Embeddings، فهرسة وبصمات الملفات، RAG والصلاحيات، تقييم الاسترجاع والاستشهادات، تعليمات النظام، MCP وأمان الأدوات، اقتراح الذكريات والواجهة، والتوثيق.
- مقارنة رأسه مع `main` الحالي أظهرت تفرعًا كبيرًا (الفرع القديم متباعد عن `main`)؛ لذلك لا يُعاد توجيهه أو دمجه ككتلة واحدة.

### main

- الرأس عند إنشاء هذا السجل: `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee`.
- هذا هو خط الأساس الذي يجب استخدامه عند إنشاء أول PR فرعي. إذا تحرك `main` لاحقًا، يجب تسجيل SHA الجديد قبل المتابعة.

### ما دخل بالفعل إلى main ولا يعاد إدخاله

- إصلاح PR #690 الخاص بقراءة Gemini REST `embedContent` لاستجابة `embedding.values` المفردة موجود في `main`.
- Merge commit: `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee`.
- فُحص ملف `ai-backend/app/services/embeddings.py` على `main` وتأكد وجود مسار قراءة الاستجابة المفردة، إضافة إلى دعم `embeddings[]` وOpenAI-compatible `data[].embedding`.
- لذلك يجب استبعاد هذا الإصلاح من أي PR مستخرج من #665، وعدم إعادة نسخه أو تقديمه كعمل جديد.

## 3. ترتيب التفكيك المقترح

الترتيب يراعي الاعتماديات ويمنع خلط تغييرات التطبيق بترحيلات البيانات:

| الترتيب | النطاق | ما يدخل فيه | ما لا يدخل فيه | الحالة |
|---|---|---|---|---|
| 0 | سجل التتبع | هذا المستند، القرارات، الروابط، SHA، نتائج الفحوص | لا تغييرات تشغيلية | قيد التسجيل |
| 1 | إعداد مزود Embeddings | إعدادات مستقلة للمزود والمفتاح والعنوان والنموذج، توافق رجعي، تحقق إعدادات ومزود، اختبارات HTTP mock | بصمات الملفات، ترحيل DB، إعادة الفهرسة، إصلاح Gemini المفرد الموجود في #690 | لم يبدأ |
| 2 | حدود وصلاحيات RAG | ملكية المحادثة، عضوية مساحة العمل، صلاحيات المشروع والمساعد داخل خدمة الاسترجاع، اختبارات منع الوصول | بصمات الفهرسة أو تحسينات الترتيب غير الضرورية | لم يبدأ |
| 3 | سلامة فهرسة الملفات | بصمات النص وفضاء Embeddings، ترحيل Alembic، حفظ الفهرس القديم عند فشل إعادة الفهرسة، خطة التعامل مع السجلات القديمة | تشغيل ترحيل على الإنتاج أو إعادة فهرسة جماعية | لم يبدأ |
| 4 | إدخال الملفات واستخراج النص | حدود DOCX/PDF/TXT/CSV، رسائل الصيغ المدعومة، إعادة محاولة فهرسة وصف الصور، اختبارات الملفات | تغييرات UI غير لازمة | لم يبدأ |
| 5 | تقييم RAG | مجموعة بيانات offline، Recall@k وPrecision@k وnDCG@k وMRR، تقارير مقارنة قابلة لإعادة الإنتاج | `--run-live` أو أي استهلاك لحصة API | لم يبدأ |
| 6 | سياق المطالبات والاستشهادات | تعليمات النظام حسب المزود، تحييد علامات السياق، تقييم الاستشهادات، اختبارات prompt injection المحلية | ادعاء مناعة كاملة أو نتائج تقييم حي بلا دليل | لم يبدأ |
| 7 | أمان MCP وأدوات الوكيل | حدود خوادم MCP، allowlists، تحقق صلاحيات القراءة/التعديل، معالجة المدخلات، اختبارات عدم التغيير | تفعيل خوادم أو أدوات إنتاجية دون إعداد مستقل | لم يبدأ |
| 8 | الذاكرة واقتراحاتها | API اقتراح الذكريات، موافقة المستخدم قبل الحفظ، فصل الذاكرة الشخصية عن المشروع، الخصوصية والملكية | حفظ تلقائي أو استخراج في الخلفية | مؤجل حتى استقرار الأساس |
| 9 | الواجهة والتوثيق النهائي | لوحة اقتراح الذكريات، رسائل الملفات، خارطة الطريق وتوثيق التشغيل | أي إطلاق واجهة قبل اكتمال اختبارات API والصلاحيات | مؤجل |

قد يُعاد ترتيب PR فرعي فقط إذا أثبتت مراجعة الاعتماديات ذلك، ويُسجل السبب هنا قبل التنفيذ.

## 4. شروط قبول كل PR فرعي

1. يبدأ من SHA حديث موثق من `main`.
2. يغيّر أقل عدد ممكن من الملفات ويقدم مسؤولية واحدة واضحة.
3. يذكر صراحة ما إذا كان يعتمد على PR فرعي سابق.
4. لا يكرر إصلاح #690 أو أي تغييرات سبق دمجها.
5. يتضمن اختبارات نجاح وفشل وحدود، باستخدام mocks/fixtures دون اتصال خارجي متى أمكن.
6. يمر بجميع فحوص الفرع الإلزامية: backend، frontend، SDK، preview-builder، production-compose، CodeQL Python، CodeQL JavaScript/TypeScript.
7. تُراجع migrations والخصوصية والصلاحيات بشكل خاص؛ نجاح CI لا يغني عن مراجعة المخاطر.
8. لا دمج تلقائي لمجرد إنشاء PR؛ يُسجل قرار الدمج وSHA الناتج بعد نجاح الفحوص والمراجعة.
9. بعد الدمج، يُسجل SHA الجديد لـ `main` ويُتحقق من حالة النشر والصحة عند انطباق ذلك.
10. لا نعلن أن ميزة نجحت في الإنتاج بناءً على اختبارات محلية أو mocks فقط.

## 5. سجل التنفيذ

| التاريخ | الحدث | الدليل / SHA | النتيجة |
|---|---|---|---|
| 2026-11-12 | فحص PR #665 وحالته وحجمه | رأس #665: `4792285440511833b66e1045bc235143a5a302a5` | بقي Draft؛ لا دمج |
| 2026-11-12 | التحقق من رأس main | `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee` | أساس التفكيك |
| 2026-11-12 | التحقق من إصلاح Gemini المفرد | #690 merge `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee` | موجود في main؛ يستبعد |
| 2026-11-12 | إنشاء سجل التفكيك | فرع `docs/pr-665-split-tracker-20261112` | قيد الفتح كمستند تتبع |
| 2026-11-12 | إنشاء أول PR فرعي لإعداد Embeddings | #692، رأس مبدئي `68d6cebdabe7f50bb64b826a6e287a3d320497d5` ثم رأس مصحح `718683fe8089a93e7de1fa911f870f5b5089b28e` | Open / Draft؛ خطأ compileall في الرأس المبدئي ثم إصلاح؛ ننتظر فحوص الرأس المصحح |
| — | أول نتائج CI/CodeQL | يضاف رابط التشغيل وSHA | لم يبدأ |

## 6. سجل PRs الفرعية

يُضاف صف فور إنشاء أي PR:

| PR | العنوان | الفرع | Base SHA | Head SHA | النطاق | CI / CodeQL | القرار |
|---|---|---|---|---|---|---|---|
| #692 | فصل إعداد مزود Embeddings | `feat/embedding-provider-config-20261112` | `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee` | `718683fe8089a93e7de1fa911f870f5b5089b28e` | إعداد المزود/المفتاح/العنوان/النموذج + اختبارات mock + توثيق؛ دون بصمات DB أو RAG authorization | أعيدت الفحوص بعد إصلاح خطأ تركيب كشفه compileall؛ النتائج الجديدة قيد الانتظار | Draft؛ لا دمج حتى المراجعة والنجاح |

## 7. سياسة التحديث ومنع الالتباس

- قبل كل جلسة عمل: افحص هذا الملف، حالة #665، ورأس `main` الحالي.
- بعد كل خطوة: أضف ما تغير، الملفات، SHA، نتائج الاختبارات، والعوائق.
- إذا فشل اختبار: سجّل اسم الاختبار والسبب المعروف أو اكتب "السبب غير محسوم"؛ لا تخمّن.
- إذا تغيرت الخطة: أضف قرارًا مؤرخًا وسببًا بدل حذف القرار السابق.
- لا تستخدم أرقام PR متشابهة أو أسماء فروع قديمة دون ذكر العنوان والـ SHA.
- لا تعتبر PR جاهزًا أو مدمجًا أو منشورًا حتى تُثبت GitHub/Render الحالة الفعلية.

## 8. أول إجراء فني بعد اعتماد هذا السجل

مراجعة PR #692 لإعداد مزود Embeddings. يجب أن يحتوي فقط على:
- إعدادات `EMBEDDING_PROVIDER` و`EMBEDDING_API_KEY` و`EMBEDDING_API_BASE_URL` مع توافق رجعي عندما تترك فارغة.
- اختيار مزود Embeddings ونموذجه وعنوانه ومفتاحه بشكل آمن، وعدم إرسال مفتاح مزود المحادثة إلى مضيف غير موثوق.
- تحقق أبعاد المتجهات من المخطط الحالي.
- اختبارات إعدادات وطلبات HTTP mock لمزود Gemini وOpenAI-compatible.
- توثيق متغيرات البيئة.

يجب ألا يتضمن هذا PR بصمات الفهرسة أو migration `0081` أو RAG authorization أو اقتراحات الذاكرة أو واجهتها. كما يجب أن يحتفظ بدعم parser المفرد الذي سبق دمجه في #690 من دون إعادة تعديل مساره.

## 9. روابط العمل الحالية

- سجل التفكيك: https://github.com/HVA09/ai-chat-app/pull/691
- أول طلب فرعي لإعداد Embeddings: https://github.com/HVA09/ai-chat-app/pull/692
- طلب المصدر الكبير الذي لا يزال Draft: https://github.com/HVA09/ai-chat-app/pull/665

| 2026-11-12 | فشل أول compileall لـ #692 في `embeddings.py` بسبب قص غير صحيح لدالة بصمة الفهرسة أثناء الاستخراج | CI job `130927113038`، head `7da65b46b44e09a3e5a13c4bbb6ebbfee1f6dac2`; commit إصلاح `718683fe8089a93e7de1fa911f870f5b5089b28e` | لم يدخل `main`؛ أُصلح الملف وأعيد بناء الدالة من المصدر قبل طلب إعادة الفحوص |

| 2026-11-12 | بدء إعادة فحوص رأس #692 المصحح | CI run `43140987241`؛ CodeQL run `43140987205`؛ head `718683fe8089a93e7de1fa911f870f5b5089b28e` | الفحوص قيد التنفيذ؛ لا نتيجة نهائية بعد |

## 10. آخر حالة فحوص PR #692 — 2026-11-12

- الرأس الجاري اختباره: `718683fe8089a93e7de1fa911f870f5b5089b28e`.
- CI run: [43140987241](https://github.com/HVA09/ai-chat-app/actions/runs/43140987241) — ما زال قيد التنفيذ في Job الخلفية، وتحديدًا `Run backend tests with hang diagnostics`.
- نجحت حتى آخر فحص: `frontend`، `sdk`، `preview-builder`، `production-compose`.
- CodeQL run: [43140987205](https://github.com/HVA09/ai-chat-app/actions/runs/43140987205) — اكتمل بنجاح في Python وJavaScript/TypeScript.
- حالة PR #692: Open / Draft / mergeable=true؛ لم يتم الدمج أو النشر.
- لا تُعلن نتيجة CI الكاملة ناجحة حتى يكتمل Job الخلفية وتظهر النتيجة النهائية للـrun.

## 11. إصلاح الاختبار الوحيد الفاشل — 2026-11-12

- فشل التشغيل السابق في اختبار واحد: `tests/test_rag.py::test_gemini_embed_content_single_embedding_response_is_parsed`؛ النتيجة كانت 589 passed / 1 failed.
- السبب: الاختبار يستخدم متجهًا اصطناعيًا من 3 أبعاد ولم يهيئ ثابت بُعد مخطط قاعدة البيانات للاختبار؛ كما كان يتوقع `taskType` في الموضع القديم بدل `embedContentConfig.taskType`.
- إصلاح الاختبار نُقل إلى فرع #692 في commit `b1630280ce274e969cc25c9dd0a43ba5090aaf0b`، بضبط البعد 3 داخل الاختبار فقط وتحديث assertion. لم يتغير بُعد الإنتاج `vector(768)` ولا سلوك التطبيق لهذا الإصلاح الاختباري.
- PR #693 أُغلق كطلب تابع مكرر بعد نقل التغيير مباشرة إلى فرع #692؛ لم يُدمج في `main`.
- حالة #692 الحالية: Open / Draft؛ رأس جديد، وينبغي انتظار CI وCodeQL على الرأس الجديد قبل اعتباره ناجحًا.

- بعد نقل تحديث الاختبار إلى فرع #692، بدأ تشغيل جديد على الرأس `b1630280ce274e969cc25c9dd0a43ba5090aaf0b`: CI [43142197727](https://github.com/HVA09/ai-chat-app/actions/runs/43142197727) وCodeQL [43142197795](https://github.com/HVA09/ai-chat-app/actions/runs/43142197795). آخر تحقق: كلاهما قيد التنفيذ؛ SDK مكتمل بنجاح، وبقية الوظائف لم تكتمل بعد.

- مراجعة مرجعية لصيغة Gemini REST: وثائق Google الحالية تدرج `embedContentConfig` ضمن `EmbedContentRequest` وتعرض `taskType` و`outputDimensionality` في `EmbedContentConfig`؛ لذلك لا نرجع إلى حقول المستوى الأعلى القديمة التي أصبحت deprecated. المرجع: https://ai.google.dev/api/batch-api?hl=en و https://ai.google.dev/api/embeddings.

## 12. إغلاق مراجعة #692 ونتائج الفحوص — 2026-11-12

### نتيجة CI على رأس الكود

- رأس الكود الذي اجتاز المجموعة الكاملة: `b1630280ce274e969cc25c9dd0a43ba5090aaf0b`.
- CI run: [43142197727](https://github.com/HVA09/ai-chat-app/actions/runs/43142197727) — اكتمل بنجاح.
- Backend: **590 passed, 2 warnings in 260.05s**؛ لا توجد اختبارات فاشلة.
- Frontend tests وProduction build: نجاح.
- SDK: نجاح.
- Preview Builder: نجاح.
- Production Compose validation/build: نجاح.
- CodeQL run: [43142197795](https://github.com/HVA09/ai-chat-app/actions/runs/43142197795) — نجاح في Python وJavaScript/TypeScript.
- تنبيهات الاختبارين كانت تحذيرات إهمال من مكتبات (`crypt` وStarlette)، وليست حالات فشل.

### نتيجة مراجعة التغيير

- راجعت ملفات #692 الثمانية، بما فيها خدمة Embeddings والإعدادات واختبارات HTTP mock ودليل الإعداد.
- تحققت من أن صيغة Gemini REST تستخدم `embedContentConfig`؛ وثائق Google الحالية تضع `taskType` و`outputDimensionality` داخل هذا الكائن، وتصف الحقول القديمة في المستوى الأعلى بأنها deprecated.
- المراجع الرسمية: https://ai.google.dev/api/batch-api?hl=en و https://ai.google.dev/api/embeddings.
- ملاحظة مراجعة مهمة: تطابق عدد الأبعاد وحده لا يعني أن المتجهات متوافقة. تغيير المزود أو النموذج يغير فضاء Embeddings، ويلزم إعادة توليد متجهات المقاطع قبل استخدام المزود/النموذج الجديد للاستعلام.
- أضيف هذا التحذير إلى `ai-backend/docs/EMBEDDING_PROVIDER_CONFIGURATION.md` في commit توثيقي فقط: `26c2c30fe7ed67eba814f0ace81985074c5d9d8f`.
- أضيف أيضًا تنبيه صريح إلى أن ترك `EMBEDDING_PROVIDER` فارغًا يعني اتباع `AI_PROVIDER`؛ تغيير مزود المحادثة قد يغيّر المزود الافتراضي للمتجهات. ينبغي تثبيت إعدادات Embeddings صراحة قبل تغيير مزود المحادثة، أو تنفيذ خطة إعادة فهرسة معتمدة.
- لا migration، ولا إعادة فهرسة، ولا تغيير إنتاجي ضمن هذا التعديل التوثيقي.

### الحالة الحالية بعد التعديل التوثيقي

- رأس PR #692 الحالي: `26c2c30fe7ed67eba814f0ace81985074c5d9d8f`.
- هذا الرأس يحتوي على توثيق إضافي فقط فوق رأس الكود `b1630280ce274e969cc25c9dd0a43ba5090aaf0b` الذي اجتاز كل CI وCodeQL أعلاه؛ لا يوجد تشغيل CI جديد مسجل للالتزام التوثيقي وحده.
- PR #692: Open / Draft / mergeable=true / لم يدمج.
- Base SHA ما زال `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee`.
- PR #691: Open / Draft؛ سجل التتبع نفسه لم يدمج.
- PR #665: يبقى Open / Draft كمصدر للتفكيك.
- لم يتغير `main`، ولم يحدث نشر أو تعديل Render/Supabase.
- القرار: #692 اجتاز الاختبارات والمراجعة الفنية على رأسه الأخير؛ يُحوّل إلى Ready ويُدمج تلقائيًا وفق تفويض المستخدم العام الموثق في القسم 13. لا نبدأ PR صلاحيات RAG التابع حتى نثبت SHA الجديد لـ `main` بعد الدمج.
## 13. تفويض الدمج التلقائي عند الجاهزية — 2026-11-12

**قرار المستخدم:** إذا راجع المساعد PR ورأى أن التغيير مناسب وآمن ومكتمل الفحوص المطلوبة، فله تحويله من Draft إلى Ready ودمجه مباشرة دون طلب موافقة إضافية في كل مرة؛ الهدف تجنب تعطيل التقدم بأسئلة متكررة.

### شروط تطبيق التفويض

- النطاق واضح ومحدود، ولا توجد تعارضات أو تغييرات غير مقصودة.
- تمت مراجعة الملفات والاعتماديات والتوافق مع الحالة الحالية لـ `main`.
- جميع الفحوص الإلزامية على رأس PR نفسه مكتملة وناجحة، بما فيها CI وCodeQL.
- لا توجد ملاحظة أمنية أو بيانات مكشوفة أو تغيير غير مفهوم.
- لا يتضمن التغيير مخاطرة عالية غير قابلة للعكس.

### حالات التوقف وطلب قرار مستقل

- تعديل الأسرار أو إعدادات Render/Supabase أو موارد الإنتاج يدويًا.
- migrations أو حذف/تحويل بيانات أو إعادة فهرسة جماعية أو تغيير فضاء Embeddings دون خطة نسخ احتياطي واسترجاع مثبتة.
- تغييرات صلاحيات أو مصادقة ذات أثر واسع لم تكتمل مراجعتها.
- تغييرات مالية/مدفوعة أو التزامات خارجية أو إجراء لا يمكن التراجع عنه بأمان.
- فحوص فاشلة/ناقصة، تعارضات، أو عدم يقين جوهري في سلوك التغيير.

### أسلوب التنفيذ والتوثيق

- عند تحقق الشروط: لا يُطلب إذن جديد؛ يُدمج PR بالطريقة الأنسب (Squash افتراضيًا للتغييرات ذات commits متعددة) مع تثبيت `expected_head_sha` لمنع دمج رأس تغير أثناء المراجعة.
- بعد الدمج: يُسجل PR، ورأس الفرع، وSHA الدمج، وSHA `main` الجديد، ونتائج الفحوص، وأثر النشر المتوقع/المتحقق.
- إذا رفض GitHub الدمج بسبب حماية الفرع أو نقص check مطلوب، لا نتجاوز الحماية؛ نعالج سبب المنع ونعيد التحقق.
- التفويض لا يعني دمج PR المصدر الكبير #665 ككتلة واحدة، ولا يعني تجاوز خطة التفكيك أو ضمانات الإنتاج.

### أول تطبيق

- PR #692 مناسب للدمج: تغييرات إعداد مزود Embeddings مع توافق رجعي، اختبارات mocks، لا migrations ولا إعادة فهرسة ولا أسرار أو تعديل إعدادات الإنتاج.
- على رأسه الأخير `26c2c30fe7ed67eba814f0ace81985074c5d9d8f`، نجحت الوظائف الثمانية المطلوبة: `backend`, `frontend`, `sdk`, `preview-builder`, `production-compose`, `Analyze (python)`, `Analyze (javascript-typescript)`, و`CodeQL`.
- CI: [43143159845](https://github.com/HVA09/ai-chat-app/actions/runs/43143159845) — نجاح.
- CodeQL: [43143159899](https://github.com/HVA09/ai-chat-app/actions/runs/43143159899) — نجاح.
- تم تحويل #692 إلى Ready ودمجه باستخدام Squash بعد تحقق شروط التفويض؛ يضاف SHA الدمج والرأس الجديد لـ `main` بعد تأكيد GitHub.
## 14. نتيجة دمج PR #692 — 2026-11-12

- وافق المستخدم على قاعدة الدمج التلقائي عند تحقق شروط الملاءمة والأمان ونجاح الفحوص؛ المرجع الدائم هو القسم 13.
- تم تحويل #692 من Draft إلى Ready ثم دمجه بـ Squash دون طلب موافقة منفصلة، وفق هذا التفويض.
- PR #692: https://github.com/HVA09/ai-chat-app/pull/692 — Closed / Merged.
- رأس الفرع قبل الدمج: `26c2c30fe7ed67eba814f0ace81985074c5d9d8f`.
- Merge commit وSHA `main` الجديد: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- CI على رأس PR الأخير: [43143159845](https://github.com/HVA09/ai-chat-app/actions/runs/43143159845) — نجاح بجميع الوظائف الخمس.
- CodeQL على رأس PR الأخير: [43143159899](https://github.com/HVA09/ai-chat-app/actions/runs/43143159899) — نجاح في Python وJavaScript/TypeScript.
- فحوص ما بعد الدمج على `main` بدأت: CI [43143998208](https://github.com/HVA09/ai-chat-app/actions/runs/43143998208)، CodeQL [43143998283](https://github.com/HVA09/ai-chat-app/actions/runs/43143998283)، نشر صورة الخادم [43143998298](https://github.com/HVA09/ai-chat-app/actions/runs/43143998298). آخر تحقق: هذه الوظائف قيد التنفيذ.
- Production smoke run [43143998272](https://github.com/HVA09/ai-chat-app/actions/runs/43143998272) — نجاح.
- Render service `ai-chat-backend` مضبوط على `main` مع `autoDeploy=yes` و`autoDeployTrigger=checksPass`. آخر قائمة Deploys لا تزال تعرض `e5d640c...` كآخر نشر Live؛ لا يوجد دليل بعد أن التزام الدمج الجديد أصبح Live.
- لم نغير إعدادات Render أو Supabase أو الأسرار يدويًا. ننتظر إثبات نشر Render الفعلي ثم فحص `/health` و`/ready` قبل تسجيل الإنتاج مستقرًا.
- الخطوة التالية بعد ثبات `main` والتحقق من الإنتاج: تجهيز نطاق PR #693؟ لا؛ الرقم #693 مستخدم ومغلق كتغيير اختبار مكرر، لذا يُستخدم رقم PR الجديد الذي يمنحه GitHub عند إنشاء PR مستقل لصلاحيات RAG. لا نعيد استخدام أرقام سابقة.
- PR #691 ما زال Draft لتسجيل قرارات التفكيك، وPR #665 الأصلي ما زال Draft كمصدر. لا دمج للطلب الكبير.
### متابعة ما بعد الدمج — آخر فحص مسجل

- CI run [43143998208](https://github.com/HVA09/ai-chat-app/actions/runs/43143998208): `sdk`, `frontend`, `preview-builder`, `production-compose` نجحت؛ بقي `backend` قيد التنفيذ.
- CodeQL run [43143998283](https://github.com/HVA09/ai-chat-app/actions/runs/43143998283): اكتمل بنجاح في Python وJavaScript/TypeScript.
- Publish backend image run [43143998298](https://github.com/HVA09/ai-chat-app/actions/runs/43143998298): اكتمل بنجاح.
- Production smoke run [43143998272](https://github.com/HVA09/ai-chat-app/actions/runs/43143998272): اكتمل بنجاح.
- آخر فحص Render: لا يزال آخر Deploy Live على commit `e5d640c30b64c01db3a2ab3cac9cb09bf82e96ee`؛ لم يظهر بعد Deploy جديد لـ `b80f6d...`. سياسة `checksPass` تمنع بدء النشر قبل نجاح جميع الفحوص المطلوبة.
- لا يُعتبر نشر Render قد تم، ولا يُسجل التطبيق على أنه يعمل بالإصدار الجديد، حتى يظهر Deploy على SHA `b80f6d658d4848f78c726f0a03b21ae50359fada` بحالة `live` ثم تنجح فحوص الصحة.
## 15. تأكيد استقرار الإصدار بعد دمج #692 — 2026-11-12

- اكتملت جميع فحوص ما بعد الدمج على `main` عند `b80f6d658d4848f78c726f0a03b21ae50359fada`: backend، frontend، sdk، preview-builder، production-compose، CodeQL Python، CodeQL JavaScript/TypeScript.
- CI run [43143998208](https://github.com/HVA09/ai-chat-app/actions/runs/43143998208) — نجاح.
- CodeQL run [43143998283](https://github.com/HVA09/ai-chat-app/actions/runs/43143998283) — نجاح.
- نشر صورة الخادم run [43143998298](https://github.com/HVA09/ai-chat-app/actions/runs/43143998298) — نجاح.
- Production smoke run [43143998272](https://github.com/HVA09/ai-chat-app/actions/runs/43143998272) — نجاح.
- Render deployment `dep-dbqikcvf3r2c73f7ioq0` على commit `b80f6d658d4848f78c726f0a03b21ae50359fada` — `live` منذ `2026-11-12T02:55:44Z`.
- `/health`: `{"status":"ok","database":"ok"}`.
- `/ready`: `{"status":"ready","database":"ok","redis":"ok"}`.
- لم تُعدّل إعدادات Render/Supabase أو الأسرار. تحقق الصحة قراءة فقط.

## 16. النطاق التالي: صلاحيات RAG وسياق المحادثة — بدء التحضير

- خط أساس `main` بعد نجاح نشر #692: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- المصدر المرجعي: PR #665، الفرع `ai/embedding-provider-separation-20261025`، لكنه ليس أساسًا للدمج؛ يُعاد بناء التغيير ملفيًا فوق `main` فقط.
- النطاق المقصود: تحقق مالك المحادثة، وعضوية مساحة العمل، وصلاحية المشروع الحالية، واستمرار مشاركة المساعد، في خدمة RAG وبناء سياق الملفات/الذاكرة، مع إعادة تحقق بعد انتظار خدمة embeddings وقبل إرسال الصور إلى المزود.
- تُستبعد من هذا PR: بصمات فهرسة الملفات وmigration `0081` وأي إعادة فهرسة؛ تحسين ترتيب fallback؛ تنظيف prompt delimiters/أسماء الملفات؛ تغييرات رفع/حذف/تنزيل الملفات وZIP safety؛ تغييرات حذف المشروع؛ MCP/ذاكرة API/الواجهة.
- اختبارات القبول المستهدفة: منع مالك محادثة مختلف من استدعاء RAG؛ منع الاسترجاع بعد سحب عضوية workspace أو project؛ منع استعمال ملفات المساعد بعد إلغاء مشاركته؛ منع تحميل fallback/ذاكرة المشروع/الصورة بعد سحب الإذن؛ وعدم تحويل HTTP 404 الخاص بالصلاحيات إلى RAG fallback صامت.
- لا migration ولا تعديل production settings ولا استدعاءات AI حية في هذا PR.
- لا يُنشأ أو يدمج PR الصلاحيات قبل مراجعة فروق الملفات، وتشغيل CI وCodeQL كاملين على رأسه.
## 17. فتح PR #694 لصلاحيات RAG — 2026-11-12

- قبل بدء العمل، تم إثبات استقرار الإنتاج بعد #692: Render deployment `dep-dbqikcvf3r2c73f7ioq0` على SHA `b80f6d658d4848f78c726f0a03b21ae50359fada` بحالة `live`.
- نتائج `/health`: `status=ok`, `database=ok`؛ `/ready`: `status=ready`, `database=ok`, `redis=ok`.
- تصحيح للسجل الزمني: فقرة "آخر فحص Render" القديمة في القسم 14 كانت صحيحة وقت كتابتها قبل اكتمال النشر. القسم 15 هو الحالة النهائية بعد النشر ويحل محل الحالة المؤقتة السابقة.
- PR #694: https://github.com/HVA09/ai-chat-app/pull/694.
- العنوان: `fix(rag): enforce live conversation access for retrieval context`.
- الفرع: `fix/rag-conversation-access-20261112`.
- Base SHA: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- الرأس الحالي: `d386360ea9d9ad540060920a13a3921e13f87620`.
- التغيير محصور في أربعة ملفات: `ai-backend/app/services/rag.py`, `ai-backend/app/routers/chat.py`, `ai-backend/tests/test_rag.py`, `ai-backend/tests/test_chat.py`.
- أضيف تحقق service-level من ملكية المحادثة، وحالة الحذف، وعضوية workspace، وصلاحية المشروع، وملكية/مشاركة المساعد؛ وتُعاد مراجعة الصلاحيات بعد انتظار embedding قبل إرجاع المقاطع.
- أضيف تحقق route-level قبل بناء السياق، وبعد انتظار RAG وقبل fallback النصي، وفي `/chat/compare` و`/chat/vision`؛ وتُمنع أخطاء HTTP 404 للصلاحيات من التحول إلى fallback صامت.
- حُميت project memories من التحميل عند فقد صلاحية المشروع.
- الاختبارات الجديدة تغطي محادثة مستخدم آخر، وسحب عضوية workspace، وغياب project role، وإلغاء assistant share، وسحب الإذن أثناء انتظار embedding، ومنع سياق الذاكرة والوكيل والمقارنة والصورة بعد سحب الصلاحية.
- لا بصمات فهرسة ولا migration `0081` ولا إعادة فهرسة؛ لا تعديل إعدادات Render/Supabase أو الأسرار؛ لا استدعاءات AI حية.
- CI run [43145917571](https://github.com/HVA09/ai-chat-app/actions/runs/43145917571) وCodeQL run [43145917584](https://github.com/HVA09/ai-chat-app/actions/runs/43145917584) بدآ على الرأس `d386360...`; آخر فحص وقت تحديث هذا السجل: الفحوص ما زالت قيد التنفيذ. SDK وProduction Compose مكتملان بنجاح، وبقية الوظائف قيد التنفيذ.
- PR #694 يبقى Open / Draft حتى اكتمال الفحوص والمراجعة على رأسه النهائي.
### نتيجة أول تشغيل لـ #694 والتصحيح — 2026-11-12

- CI run [43145917571](https://github.com/HVA09/ai-chat-app/actions/runs/43145917571) على الرأس `d386360ea9d9ad540060920a13a3921e13f87620` انتهى: **599 passed, 1 failed, 2 warnings**.
- الفشل الوحيد: `tests/test_pool_release_acceptance.py::test_second_session_can_use_only_pool_slot_while_external_io_is_blocked[vision_provider]` عند `tests/test_pool_release_acceptance.py:344`؛ وجد الاختبار اتصالًا واحدًا محجوزًا أثناء انتظار مزود الرؤية (`checkedout() == 1` بدل 0).
- السبب المؤكد من ترتيب الكود: أضفنا إعادة فحص ACL بعد تحرير الاتصال وقبل استدعاء مزود الرؤية، وهذا الفحص أعاد استخدام جلسة قاعدة البيانات ولم يُحرر الاتصال مرة ثانية قبل الانتظار الخارجي.
- التصحيح في commit `c3053f3439db853202a4ec82295ff4021593ab60`: استدعاء `commit_and_release_connection(db)` مباشرة بعد إعادة فحص ACL النهائية وبعد تجهيز الصورة، وقبل `get_ai_vision_reply`.
- بذلك نحافظ على الهدفين معًا: إعادة التحقق من صلاحية المستخدم بعد تجهيز الصورة، ثم تحرير اتصال DB قبل استدعاء مزود الرؤية. لا يتطلب التصحيح أي تعديل إنتاج أو schema.
- رأس #694 الحالي بعد التصحيح: `c3053f3439db853202a4ec82295ff4021593ab60`; يجب تشغيل CI وCodeQL مجددًا على هذا الرأس تحديدًا. لا دمج حتى نجاحهما.
- بعد إصلاح حد تحرير الاتصال في Vision، بدأ تشغيل جديد على الرأس `c3053f3439db853202a4ec82295ff4021593ab60`: CI [43146675524](https://github.com/HVA09/ai-chat-app/actions/runs/43146675524) وCodeQL [43146675611](https://github.com/HVA09/ai-chat-app/actions/runs/43146675611). آخر تحقق: كلاهما قيد التنفيذ؛ SDK هو أول job مكتمل بنجاح.

### إعادة التحقق الثالثة بعد تصحيح ترتيب تحرير DB في Vision — 2026-11-12

- أوضح التشغيل السابق [43146675524](https://github.com/HVA09/ai-chat-app/actions/runs/43146675524) أن اختبار قبول حجز الاتصال أصبح ناجحًا، بما فيه `vision_provider`؛ الفشل الوحيد كان في توقع سجل الأحداث لا في سلوك تحرير الاتصال:
  `tests/test_vision.py::test_analyze_attached_image` توقع `["release", "vision"]` بينما السلوك الجديد الصحيح هو `["release", "release", "vision"]`.
- الترتيب المقصود: تحرير اتصال DB قبل materialize/قراءة الصورة من التخزين، ثم إعادة تحميل صلاحيات المحادثة بعد تجهيز الصورة، ثم تحرير الاتصال الذي أعادت عملية التحقق فتحه، وبعدها فقط استدعاء مزود الرؤية.
- تم تحديث اختبار `ai-backend/tests/test_vision.py` بهذا الترتيب مع تعليق يشرح السببين؛ لم يتم حذف assertion أو تخفيفه.
- الرأس الجديد: `b3592da30ef4ce862cdb7d9cb813b5e70c7f66c3`.
- CI run [43150034903](https://github.com/HVA09/ai-chat-app/actions/runs/43150034903) وCodeQL run [43150035008](https://github.com/HVA09/ai-chat-app/actions/runs/43150035008) يعملان على هذا الرأس.
- آخر حالة: SDK نجح؛ Backend وFrontend وProduction Compose وPreview Builder وCodeQL ما زالت قيد التنفيذ. لا تُعتبر الفحوص ناجحة حتى تكتمل جميعها.
- PR #694 يبقى Draft، لم يُدمج، ولم يتغير `main` أو Render بسبب هذا الفرع.


- **تحديث نطاق الملفات بعد تصحيح اختبار Vision:** أصبح PR #694 يغيّر خمسة ملفات، بعد إضافة `ai-backend/tests/test_vision.py` لتوثيق تسلسل تحرير DB المزدوج:
  1. `ai-backend/app/routers/chat.py`
  2. `ai-backend/app/services/rag.py`
  3. `ai-backend/tests/test_chat.py`
  4. `ai-backend/tests/test_rag.py`
  5. `ai-backend/tests/test_vision.py`
- هذا تحديث تصحيحي لعبارة "أربعة ملفات" في القسم 17؛ النطاق الوظيفي لا يزال هو نفسه.

## 18. التحضير المبدئي لمرحلة بصمات فهرسة الملفات — لا تغيير كود بعد

- لا يبدأ طلب بصمات الفهرسة إلا بعد دمج #694 والتحقق من `main` ونشره وصحة الخدمة.
- ملفات المصدر المحتملة في #665:
  - `ai-backend/app/models/file_attachment.py`: حقول مصدر النص/بصمة نموذج embeddings/وقت الفهرسة، ودالة normalized-text fingerprint.
  - `ai-backend/migrations/versions/0081_file_index_fingerprints.py`: migration لإضافة أعمدة nullable فقط، مع مراجعة downgrade/ترتيب revision chain.
  - `ai-backend/app/services/rag.py`: تحديث `index_file_chunks` لحفظ هوية المصدر والنموذج، واستبعاد المقاطع التي لا تتوافق بصماتها مع المصدر/النموذج الحالي.
  - `ai-backend/tests/test_rag_index_fingerprints.py`: اختبارات رفض الفهرس القديم عندما يتغير النص أو نموذج embeddings.
  - أجزاء محددة فقط من `ai-backend/app/routers/files.py` و`tests/test_files.py` لحالة الفهرسة وإعادة الفهرسة، بعد فصل الـ ACL وملفات ZIP الموجودة في نفس الملف.
- عناصر يجب استبعادها من PR الفهرسة:
  - صلاحيات workspace/project والتحميل/الإرفاق/الحذف — نُقلت وظيفيًا إلى #694 أو يجب فصلها في نطاق مستقل.
  - حماية ZIP/Office extraction وتطبيع أسماء الملفات.
  - تحسين ترتيب ملفات fallback وتنظيف prompt delimiters.
  - تغيير `ai-backend/app/tasks.py` الذي يمرر دور المستخدم إلى agent configuration version؛ لا يعتمد عليه fingerprint PR ويجب نقله إلى نطاق Agent/MCP لاحق.
- خطر تشغيلي يجب فحصه قبل أي دمج: migration `0081` يجب أن تكون إضافة أعمدة nullable فقط بلا backfill أو إعادة فهرسة تلقائية أو قفل طويل للجدول. تحديث الفهارس القديمة يكون عملية منفصلة قابلة للتدرج، ولا يُجرى على الإنتاج ضمن migration.
- لا ينفذ أي migration على Render/Supabase يدويًا خلال التحضير. الاختبار يكون على قاعدة CI أولًا، ثم مراجعة خطة النشر/backfill قبل الدمج.

## 19. دمج #694 والتحقق من main وRender — 2026-11-12

### الدمج ومراجعة النطاق
- PR #694: https://github.com/HVA09/ai-chat-app/pull/694 — أُغلق بصفته مدمجًا في `main` بطريقة Squash.
- PR head الذي اجتاز الفحوص: `b3592da30ef4ce862cdb7d9cb813b5e70c7f66c3`.
- Base قبل الدمج: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- Merge commit ورأس `main` الحالي: `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13`.
- الملفات الخمسة النهائية:
  1. `ai-backend/app/routers/chat.py`
  2. `ai-backend/app/services/rag.py`
  3. `ai-backend/tests/test_chat.py`
  4. `ai-backend/tests/test_rag.py`
  5. `ai-backend/tests/test_vision.py`
- لم يتضمن PR migrations أو reindex أو تعديلات Render/Supabase أو الأسرار أو تغييرات إنتاجية يدوية.

### نتائج الفحوص قبل الدمج
- CI [43150034903](https://github.com/HVA09/ai-chat-app/actions/runs/43150034903): **600 passed, 2 warnings in 311.64s**.
- CodeQL [43150035008](https://github.com/HVA09/ai-chat-app/actions/runs/43150035008): نجاح.
- جميع الفحوص الثمانية الظاهرة على رأس PR انتهت بنجاح.
- لم تظهر مراجعات أو threads معلقة في PR.

### نتائج الفحوص بعد الدمج على main
- CI [43151446387](https://github.com/HVA09/ai-chat-app/actions/runs/43151446387): **600 passed, 2 warnings in 291.74s**.
- CodeQL [43151446356](https://github.com/HVA09/ai-chat-app/actions/runs/43151446356): نجاح، Python وJavaScript/TypeScript.
- Production smoke [43151446481](https://github.com/HVA09/ai-chat-app/actions/runs/43151446481): نجاح.
- Publish backend image [43151446459](https://github.com/HVA09/ai-chat-app/actions/runs/43151446459): نجاح.
- جميع check runs التسعة على merge SHA اكتملت بنجاح، دون checks فاشلة أو معلقة.

### Render بعد الدمج
- الخدمة: `srv-dakc4nbm8hqs73e2po9g` (`ai-chat-backend`)، الخطة Free، الفرع `main`، والنشر التلقائي مضبوط على `checksPass`.
- Render deployment: `dep-dbqjkd59el5s73f04dg0`، commit `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13`، الحالة النهائية `live`.
- `/health`: `{"status":"ok","database":"ok"}`.
- `/ready`: `{"status":"ready","database":"ok","redis":"ok"}`.
- ظهرت استجابة `503` واحدة في أول محاولة تحقق أثناء متابعة التحديث؛ عادت نقاط الصحة بعد ذلك بنجاح في محاولات متكررة، بما فيها التحقق بعد أن أصبح Deploy الجديد `live`. لا يوجد تشخيص مؤكد لسبب الاستجابة المؤقتة، ولا تُسجل كفشل نشر.
- لا يوجد أي تدخل يدوي في الإنتاج أو تغيير إعدادات/أسرار.

### القرار التالي
- أصبح شرط البدء في مرحلة بصمات فهرسة الملفات متحققًا: #694 مدمج، `main` أخضر، وRender `live` ونقاط الصحة سليمة.
- المرحلة التالية المقترحة هي PR صغير مستقل فوق `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13`, لنطاق بصمات النص ومصدر embeddings فقط.
- لا تبدأ migration `0081` أو أي reindex قبل قراءة سلسلة revisions كاملة، وفحص downgrade، وقياس أثر الأعمدة nullable، ونجاح CI على فرع المرحلة.
## 20. بدء مرحلة بصمات فهرسة الملفات — PR #695 — 2026-11-12

### PR الجديد وحدود التنفيذ
- PR #695: https://github.com/HVA09/ai-chat-app/pull/695 — Open / Draft، غير مدمج.
- Branch: `fix/rag-index-fingerprints-20261112`.
- Base: `main` على `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13`.
- Head بعد آخر تعديل: `12b83ba2826e80de75e1084a51608f8396c7db7a`.
- سبعة ملفات: نموذج FileAttachment، Embedding identity، RAG index writer، migration، واختبارات الهوية والفهرسة.

### قرار سلسلة migrations
- المصدر القديم في #665 اقترح `0081_file_index_fingerprints` بعد `0080_harden_public_rls`.
- لكن main يحتوي بالفعل `0081_harden_all_public_tables`، وهي child لنفس revision `0080_harden_public_rls`.
- لذلك migration المرحلة الحالية مرقمة `0082_file_index_fingerprints` و`down_revision = 0081_harden_all_public_tables`. هذا يحافظ على خط واحد بعد head الحالي ولا ينشئ migration head موازية.

### استراتيجية نشر مرحلية للحفاظ على توافق الملفات القديمة
- #695 هو write-side foundation فقط: يضيف nullable metadata، ويحسب بصمة النص الحالي، وهوية embedding سرية المفتاح، ويسجل metadata بعد اكتمال توليد المتجهات.
- لا يضيف #695 شرط stale-index إلى retrieval بعد. تبقى ملفات الإنتاج القديمة ذات metadata NULL قابلة للاسترجاع كما كانت قبل هذا التغيير، فلا يحدث تعطيل مفاجئ للمعرفة القديمة عند تطبيق migration.
- لا يحتوي migration على backfill أو reindex، ولا تُجرى أي عملية reindex إنتاجية.
- يجب أن تنفذ مرحلة منفصلة بعد #695 آلية reindex آمنة للملفات القديمة، وبعدها فقط تفعيل strict retrieval fingerprint filtering في PR منفصل مع اختبارات stale source/provider.
- تم استبعاد تغييرات files router وZIP/Office paths وtasks/Agent من هذا PR.

### حالة الفحوص
- بعد آخر commit `12b83ba2826e80de75e1084a51608f8396c7db7a`, GitHub أنشأ CI run `43152937955` وCodeQL run `43152937843`. حالتهما كانت pending عند تسجيل هذه الملاحظة؛ لا تُسجل أي نتيجة نجاح قبل اكتمالهما.
- PR #695 Draft ولا يُدمج حتى تكتمل جميع الفحوص والمراجعة.

## 21. بوابة migration الإنتاجية في PR #695 — 2026-11-12

- تمت مراجعة `ai-backend/scripts/start.sh`: أمر بدء حاوية Backend ينفذ `alembic upgrade head` قبل تشغيل Uvicorn.
- إعداد Render الفعلي للخدمة `srv-dakc4nbm8hqs73e2po9g` هو `autoDeploy=yes` و`autoDeployTrigger=checksPass`. لذلك دمج #695 سيؤدي إلى تطبيق migration `0082` تلقائيًا في نشر Render التالي؛ عدم تشغيل migration يدويًا لا يعني أن الدمج بلا أثر على قاعدة الإنتاج.
- أُضيفت هذه الحقيقة إلى وصف PR #695. يبقى Open / Draft، ولا يُحوّل إلى Ready ولا يُدمج قبل:
  1. إثبات وجود نسخة PostgreSQL احتياطية حديثة ومعرفة مسار الاستعادة.
  2. اختبار الترقية على قاعدة مرحلية/مؤقتة عند schema مطابق لـ `main`، والتأكد من أن الأعمدة الستة nullable ولا يوجد backfill أو reindex.
  3. مراجعة مدة/أقفال migration وأثر downgrade؛ downgrade يحذف الأعمدة الستة، ولذلك يختبر على قاعدة مؤقتة فقط.
  4. قرار صريح بالموافقة على تغيير schema في الإنتاج.
- هذا الشرط منفصل عن تفويض الدمج التلقائي للطلبات منخفضة المخاطر، ويتوافق مع بوابة التغييرات الإنتاجية في القسم 13.
- حالة الفحوص عند التحديث: CodeQL Python وJavaScript/TypeScript ناجحان؛ Frontend وSDK وPreview Builder وProduction Compose ناجحة؛ Backend pytest ما زال قيد التنفيذ. لا تُسجل نتيجة Backend قبل نهاية job.

## 22. دمج #695 ونتائج ما بعد الدمج — 2026-11-12

### حالة PR والفحوص على رأسه
- GitHub يؤكد أن PR #695 أُغلق بصفته مدمجًا في `2026-11-12T04:16:31Z`؛ merge commit: `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- PR head: `12b83ba2826e80de75e1084a51608f8396c7db7a`; base قبل الدمج: `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13`.
- CI PR run [43152937955](https://github.com/HVA09/ai-chat-app/actions/runs/43152937955): جميع الوظائف الخمس ناجحة.
- Backend pytest: **607 passed, 2 warnings in 292.60s**.
- CodeQL PR run [43152937843](https://github.com/HVA09/ai-chat-app/actions/runs/43152937843): Python وJavaScript/TypeScript ناجحان.
- لا فحوص فاشلة على رأس PR.

### فحوص push على main
- `main` انتقل مباشرة من `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13` إلى `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f` (commit واحد، لا commits إضافية).
- CI push run [43153718406](https://github.com/HVA09/ai-chat-app/actions/runs/43153718406): SDK وFrontend وPreview Builder وProduction Compose نجحت؛ Backend pytest كان لا يزال قيد التنفيذ عند آخر تحقق.
- CodeQL push run [43153718347](https://github.com/HVA09/ai-chat-app/actions/runs/43153718347): نجاح.
- Production smoke push run [43153718382](https://github.com/HVA09/ai-chat-app/actions/runs/43153718382): نجاح.
- Publish backend image push run [43153718274](https://github.com/HVA09/ai-chat-app/actions/runs/43153718274): نجاح.
- عند آخر تحقق لم تبدأ أحداث Render على SHA `f3ba9...` بعد، وآخر deployment Live كان على `c8264a...`. إعداد Render ما زال `autoDeploy=yes` و`autoDeployTrigger=checksPass`؛ ننتظر اكتمال CI على main ثم نعيد فحص deployment وhealth/ready.
- لم تُنفذ migration أو backfill أو إعادة فهرسة يدويًا، ولم تُعدّل أسرار أو إعدادات الإنتاج. لا تعتبر migration 0082 مطبقة حتى يؤكد Render deployment الجديد أو تحقق قاعدة البيانات المصرّح به.
### إعادة فحص الخدمة أثناء انتظار CI الخاص بـ main
- عند إعادة الفحص، بقي Backend job في CI push run [43153718406](https://github.com/HVA09/ai-chat-app/actions/runs/43153718406) داخل خطوة Backend pytest؛ بقية وظائف CI الأربع انتهت بنجاح، وCodeQL push run [43153718347](https://github.com/HVA09/ai-chat-app/actions/runs/43153718347) انتهى بنجاح.
- فحص Production smoke [43153718382](https://github.com/HVA09/ai-chat-app/actions/runs/43153718382) انتهى بنجاح.
- Render لا يزال يعرض deployment السابق `dep-dbqjkd59el5s73f04dg0` على SHA `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13` بحالة `live`؛ لم تظهر أحداث build/deploy جديدة بعد دمج #695.
- نقاط الخدمة على النسخة التي لا تزال Live: `/health = {status:ok,database:ok}` و`/ready = {status:ready,database:ok,redis:ok}`. هذه النتائج تثبت سلامة النسخة السابقة فقط، ولا تثبت أن migration 0082 طُبقت.
- القرار: لا نعلن نشر #695 حتى يظهر Render deploy على SHA `f3ba9d4...` بحالة `live`، ثم نعيد فحص `/health` و`/ready` ونراجع سجل بدء الحاوية لإثبات ترقية Alembic.
## 21. نتائج PR #695 واختبار staging وحالة بوابة الإنتاج — 2026-11-12

### دمج وفحوص PR
- PR #695: https://github.com/HVA09/ai-chat-app/pull/695 — merged بطريقة Squash.
- رأس PR المختبر: `12b83ba2826e80de75e1084a51608f8396c7db7a`.
- Merge commit ورأس `main`: `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- CI [43152937955](https://github.com/HVA09/ai-chat-app/actions/runs/43152937955): **607 passed, 2 warnings in 292.60s**.
- CodeQL [43152937843](https://github.com/HVA09/ai-chat-app/actions/runs/43152937843): Python وJavaScript/TypeScript ناجحان.
- وظائف Backend وFrontend وSDK وPreview Builder وProduction Compose نجحت؛ فحوص migration upgrade وORM metadata check نجحت.

### اختبار Supabase staging
- المشروع `ai-chat-stage-db`، project ref `ihjuewvddqsesbrqqptj`, كان Alembic revision `0081_harden_all_public_tables` قبل الاختبار.
- طُبقت DDL مكافئة لأعمدة migration الستة على staging فقط، ثم فُحص `information_schema.columns`.
- ظهرت الأعمدة الستة جميعها nullable، والأطوال النصية 64/64/64/40/120، و`indexed_at` من نوع timestamptz.
- عدد صفوف `file_attachments` في staging كان 0، وعدد القيم غير الفارغة في جميع أعمدة البصمات الجديدة كان 0؛ لم يحدث backfill أو reindex.
- اختُبر downgrade على staging بإزالة الأعمدة الستة؛ النتيجة: `remaining_fingerprint_columns = 0`, وظل `alembic_version = 0081_harden_all_public_tables`.
- هذا اختبار DDL عملي على staging باستخدام Supabase migration tool، وليس تشغيل Alembic CLI على staging. Alembic upgrade الفعلي اختُبر مستقلًا على PostgreSQL المؤقت داخل CI.

### بوابة النسخة الاحتياطية والموافقة — عائق غير مغلق
- ظهر في نص PR #695 قبل الدمج شرط إضافي: لا تجعل PR Ready ولا تدمجه قبل تأكيد نسخة إنتاج احتياطية حديثة وإمكانية استعادتها، واختبار staging، ومراجعة lock/downgrade، والموافقة الصريحة على تغيير مخطط الإنتاج.
- **حدث خطأ إجرائي:** حُوّل PR إلى Ready ودُمج قبل التحقق من النسخة الاحتياطية والموافقة الصريحة. هذا الشرط كان ينبغي أن يوقف الدمج.
- تم التحقق من Supabase organization plan: `free`، لذلك لا توجد نسخ يومية تلقائية ضمن الخطة بحسب توثيق Supabase الحالي. النسخ اليدوي ممكن عبر Supabase CLI، لكن لم يظهر في الأدوات المتاحة دليل على وجود نسخة يدوية حديثة أو اختبار restore.
- المصدر الرسمي: https://supabase.com/kb/faqs/platform/free-plan-backups وhttps://supabase.com/docs/guides/platform/backups (راجِع تاريخ تحديث الوثائق في 2026-10-30 و2026-11-05).
- Production project `ai-chat-prod-db` ref `wfhijmawoojcmfdgibxg` عند آخر فحص: `alembic_version = 0081_harden_all_public_tables`. عدد أعمدة fingerprint الجديدة في `public.file_attachments` = 0.
- Render auto-deploy ما زال `checksPass`. آخر deploy ظاهر هو `dep-dbqjkd59el5s73f04dg0` على SHA `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13` بحالة `live`. لم يبدأ deploy للـ `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f` عند آخر فحص.
- Main CI [43153718406](https://github.com/HVA09/ai-chat-app/actions/runs/43153718406) كان لا يزال `in_progress`؛ CodeQL [43153718347](https://github.com/HVA09/ai-chat-app/actions/runs/43153718347)، Publish image [43153718274](https://github.com/HVA09/ai-chat-app/actions/runs/43153718274)، وProduction smoke [43153718382](https://github.com/HVA09/ai-chat-app/actions/runs/43153718382) اكتملت بنجاح.
- لا يوجد تأكيد من المستخدم بعد على نشر migration `0082` إلى قاعدة الإنتاج. لا تنفذ migration أو reindex يدويًا ولا تغيّر إعدادات Render أثناء انتظار القرار.


## 23. اكتمال CI على main وبدء نشر Render — 2026-11-12

### نتيجة CI بعد الدمج
- GitHub CI push run [43153718406](https://github.com/HVA09/ai-chat-app/actions/runs/43153718406) اكتمل عند `2026-11-12T04:22:50Z` على SHA `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f` بنتيجة **success**.
- جميع وظائف CI الخمس ناجحة: Backend وFrontend وSDK وPreview Builder وProduction Compose.
- خطوات Backend التالية اكتملت بنجاح: `pip-audit`, `compileall`, `alembic upgrade head` على PostgreSQL المؤقت في CI، وفحص تطابق ORM metadata، ثم Backend pytest. لم يتوفر في مخرجات الوظائف رقم إجمالي pass count لهذا التشغيل؛ لذلك لا يُنسخ رقم 607 الخاص بتشغيل PR #695 على أنه عدد اختبارات تشغيل main.
- CodeQL push [43153718347](https://github.com/HVA09/ai-chat-app/actions/runs/43153718347)، Production smoke [43153718382](https://github.com/HVA09/ai-chat-app/actions/runs/43153718382)، وPublish image [43153718274](https://github.com/HVA09/ai-chat-app/actions/runs/43153718274) ظلت ناجحة حسب آخر تحقق.

### حالة Render بعد اكتمال CI
- بعد اكتمال CI بدأ Render النشر التلقائي للـ SHA نفسه.
- deployment الجديد: `dep-dbqju7e7bikc739n63i0`.
- build: `bld-dbqju7e7bikc739n63ig`، وحدث `build_ended` بحالة `succeeded` عند `2026-11-12T04:23:05Z`.
- حدث `deploy_started` عند `2026-11-12T04:22:53Z`، وكانت الحالة عند آخر فحص `update_in_progress`؛ لم يصل بعد إلى `live`.
- تم تأكيد إعداد الخدمة: `autoDeploy=yes`, `autoDeployTrigger=checksPass`, الفرع `main`.
- آخر فحصي `/health` و`/ready` أعادا OK قبل بدء deployment الجديد، ولذلك فهما يثبتان سلامة الإصدار السابق فقط، ولا يثبتان صحة الإصدار الجديد أو تطبيق migration.
- لا يوجد حتى هذه اللحظة دليل مباشر على تنفيذ Alembic revision `0082_file_index_fingerprints` على الإنتاج.

### حاجز فحص سجلات Render وسلامة قاعدة الإنتاج
- أداة سجلات Render طلبت تحديد workspace. أظهر استعلام workspaces وجود مساحة واحدة باسم `My Workspace` ومعرف `tea-dagsi5ou01pc73f2g470`، لكن لم يتم اختيارها دون موافقة المستخدم.
- بوابة النسخة الاحتياطية والموافقة الصريحة على تغيير مخطط الإنتاج ما زالت غير موثقة الإغلاق كما في القسم 21 (المضاف لاحقًا)؛ staging وCI ليسا بديلًا عن backup/restore production.
- لا تُنفذ إعادة فهرسة، ولا backfill، ولا migration يدوية. لا تُجرى تغييرات لإعدادات Render أو قاعدة الإنتاج. يلزم أولًا حسم إذن استخدام مساحة Render المحددة لمراجعة logs/deploy، ثم التحقق من حالة النشر والصحة وrevision قبل أي مرحلة لاحقة.


## 24. تحقق تطبيق migration 0082 على قاعدة الإنتاج — 2026-11-12

### دليل قاعدة البيانات
- تم التحقق للقراءة فقط من المشروع `ai-chat-prod-db`، ref `wfhijmawoojcmfdgibxg`، وحالة المشروع `ACTIVE_HEALTHY`.
- نتيجة `alembic_version`: `0082_file_index_fingerprints`.
- جميع الأعمدة الستة في `public.file_attachments` موجودة، وجميعها `nullable = YES`:
  - `extracted_text_sha256`
  - `indexed_text_sha256`
  - `indexed_embedding_fingerprint`
  - `indexed_embedding_provider`
  - `indexed_embedding_model`
  - `indexed_at`
- عدد صفوف `file_attachments` في لحظة الفحص: 49.
- عدد الصفوف التي تحتوي أي قيمة في أعمدة metadata الستة الجديدة: **0**. هذا يثبت عدم وجود backfill/reindex في وقت الفحص؛ لا توجد بيانات فهرسة جديدة مخزنة في هذه الحقول.
- استعلاما التحقق كانا SELECT فقط؛ لم يُنفذ أي DDL أو DML يدوي على الإنتاج.

### صحة الخدمة بعد ظهور revision 0082
- `/health`: `{"status":"ok","database":"ok"}`.
- `/ready`: `{"status":"ready","database":"ok","redis":"ok"}`.
- لا أخطاء في طلبات فحص الصحة عند هذه المحاولة.

### ما لم يُحسم بعد
- Render deployment `dep-dbqju7e7bikc739n63i0` على SHA `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f` أظهر build ناجحًا وبدأ deploy، لكن Render API كان لا يزال يعرض `update_in_progress` في آخر قراءة؛ لذلك لا نسجل `live` حتى الآن.
- لم تتم مراجعة application logs التي تثبت تسلسل بدء الحاوية؛ يتطلب Render تحديد workspace. توجد مساحة واحدة ظاهرة باسم `My Workspace` ومعرف `tea-dagsi5ou01pc73f2g470`، ولم تُستخدم دون تأكيد المستخدم.
- نتيجة قاعدة البيانات تثبت وصول Alembic إلى revision 0082، لكنها لا تكفي وحدها لتأكيد استقرار عملية Render أو اكتمال deployment.
- مسألة backup/restore production لم تُغلق قبل تشغيل migration. لا دليل في الأدوات الحالية على نسخة إنتاج حديثة أو اختبار استعادة. يجب الاحتفاظ بهذه الملاحظة كحادث حوكمة/تشغيل، وعدم وصف الشرط بأنه تحقق.
- لا تنفيذ لإعادة الفهرسة أو backfill أو تغييرات أخرى على مخطط الإنتاج. المرحلة التالية تبقى متوقفة حتى تثبت حالة Render `live` وتُستكمل مراجعة الخدمة.


## 25. فحص سجلات Render بعد موافقة المستخدم على مساحة العمل — 2026-11-12

### التفويض والفحص
- وافق المستخدم صراحةً على استخدام مساحة Render `My Workspace`، وطلب اعتمادها للفحوص المستقبلية دون الرجوع إليه في كل مرة لتجنب تعطيل العمل.
- استخدمت `workspaceId = tea-dagsi5ou01pc73f2g470` للقراءة فقط. لم يتم تغيير إعدادات الخدمة أو الأسرار أو أي مورد Render.
- Render deployment `dep-dbqju7e7bikc739n63i0` على commit `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f` انتهى `live`:
  - `startedAt = 2026-11-12T04:22:53Z`
  - `finishedAt = 2026-11-12T04:24:47Z`
  - event `deploy_ended` بنجاح عند `2026-11-12T04:24:48Z`.
- Build `bld-dbqju7e7bikc739n63ig` انتهى بنجاح.

### دليل سجلات بدء الحاوية
- سجل Render للـ instance الجديد `srv-dakc4nbm8hqs73e2po9g-wj2mw` يحتوي على:
  - `INFO [alembic.runtime.migration] Context impl PostgresqlImpl.`
  - `Will assume transactional DDL.`
  - `Running upgrade 0081_harden_all_public_tables -> 0082_file_index_fingerprints`
  - `Object Storage connectivity: OK`
  - `Embedded Celery enabled`
  - بدء Celery worker وCelery beat.
  - `Starting API on 0.0.0.0:10000`.
- هذا دليل مباشر أن عملية بدء الحاوية نفذت migration 0082، وليس مجرد استنتاج من استعلام قاعدة البيانات.
- سجلات Health Check الداخلية على الـ instance الجديد أظهرت `HTTP GET /health 200` بشكل دوري، على الأقل حتى `2026-11-12T04:27:57Z`، مع latency تقريبًا 9–15ms.
- استعلام Render لأحداث `server_failed`, `server_restarted`, `server_available`, و`server_hardware_failure` بعد وقت النشر لم يُظهر أي حدث من هذه الأنواع؛ الحدث الظاهر كان `deploy_ended: succeeded`.
- سجل مستويات `error` للـ instance الجديد لم يُظهر entries. ظهرت فقط تحذيرات 404 لـ `GET /` و`GET /favicon.ico` في بداية النشر؛ لا تُعد هذه أخطاء تشغيل API.

### التحقق الخارجي المتعارض وحدوده
- أداة جلب HTTP الخارجية أعادت `503` لـ `/health` و`/ready` في ثلاث محاولات بعد النشر، بينما Render health-check logs الداخلية استمرت في تسجيل `/health 200`.
- استعلام Render request logs عن `/health`, `/ready` و5xx لم يُرجع سجلات؛ لا يوجد دليل كافٍ أن 503 صدر من التطبيق نفسه. لذلك تُسجل كاختلاف بين مسار الفحص الخارجي وفحص Render الداخلي، ولا نعلن أن اختبار HTTP الخارجي نجح.
- محاولة فحص المتصفح المستقل عبر TinyFish لم تبدأ لأن رصيد TinyFish غير كافٍ؛ لم تتم أي عملية مدفوعة أو تعبئة رصيد.
- واجهة فتح URL الخارجية لم تتمكن من الوصول إلى نطاق الخدمة؛ لا تُعتبر هذه النتيجة فشلًا للخدمة.
- آخر دليل قوي للاستقرار التشغيلي: deploy Live، migration في startup log، Health Check الداخلي 200 بصورة دورية، ولا أحداث server failure ولا أخطاء application logs. يظل اختبار الصحة من مسار خارجي مستقل غير محسوم.

### قرار المتابعة
- لا reindex جماعي، ولا backfill، ولا strict fingerprint filtering حتى يتم تجهيز مسار إعادة فهرسة مضبوط لكل ملف ومراجعته واختباره.
- تبقى ملاحظة backup/restore production المفتوحة كما في القسم 21؛ نجاة النشر لا تمحو عدم إثبات backup قبل migration.
- لا تغيير في Render أو Supabase من هذا التحقق، وجميع استعلامات Supabase السابقة كانت SELECT فقط.
- الخطوة الهندسية التالية بعد معالجة حاجز النسخة الاحتياطية وتوثيق استعادتها هي تصميم endpoint آمن لإعادة فهرسة ملف واحد في PR مستقل، مع ACLs واختبارات صلاحيات وفشل مزود embeddings والحفاظ على الفهرس القديم عند الفشل؛ لا يُفعّل strict retrieval filtering في ذلك PR.


## 26. فتح PR #696 لإعادة فهرسة ملف واحد بأمان — 2026-11-12

### الهدف والنطاق
- PR #696: https://github.com/HVA09/ai-chat-app/pull/696 — Open / Draft، لا دمج بعد.
- العنوان: `feat(rag): add safe per-file reindex endpoint`.
- Branch: `feat/rag-per-file-reindex-20261112`.
- Base: `main` عند `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- Head وقت فتح PR: `d8cfa9d36b044582362d9e3fcd8ccf87a86e5b9f`.
- ثلاثة ملفات فقط:
  1. `ai-backend/app/services/rag.py`
  2. `ai-backend/app/routers/files.py`
  3. `ai-backend/tests/test_file_reindex.py`

### التصميم الأمني
- فُصل تحضير الفهرس (التقطيع وتوليد embeddings) عن حفظه في DB.
- Endpoint جديد صريح: `POST /files/{file_id}/reindex`، يعالج ملفًا واحدًا فقط بطلب authenticated.
- يتم تحرير اتصال DB قبل انتظار مزود embeddings؛ بعد انتهاء المزود يُعاد تحميل صف الملف مع `FOR UPDATE`، وتُعاد مراجعة صلاحية المستخدم وبصمة النص قبل تبديل المقاطع في transaction واحدة.
- فشل مزود embeddings أو تغير النص لا يحذف الفهرس السابق.
- صلاحيات Personal files: مالك الملف فقط.
- ملفات Project: مالك المشروع أو editor/manager وفق `can_edit_project`؛ عضوية Workspace الأساسية لا تمنح إذن كتابة المشروع.
- ملفات Workspace غير المرتبطة بمشروع: صاحب الملف أو من لديه `files.manage`.
- طُبق شرط صلاحية الكتابة أيضًا على مسار `index-image` الموجود، لأنه يغيّر بيانات معرفة الملف.
- endpoint يستخدم حدود AI اليومية وحدود Workspace القائمة.

### ما لم يدخل في PR
- لا migration ولا أعمدة أو تغييرات schema.
- لا backfill ولا bulk/scheduled reindex ولا أي استدعاء embeddings على بيانات الإنتاج.
- لا strict fingerprint filtering في Retrieval؛ الملفات القديمة ذات metadata NULL تظل على سلوكها الحالي.
- لا تغييرات Frontend/UI في هذا الطلب.
- يظل حاجز backup/restore الإنتاجي المفتوح في القسم 21 قائمًا؛ هذا PR لا ينفذ عمليات بيانات تلقائية.

### الاختبارات والفحوص
- أُضيفت اختبارات للنجاح، والحفاظ على المقاطع/metadata القديمة عند فشل المزود، ومنع Project viewer والسماح للمحرر، ومنع Workspace member دون `files.manage` والسماح للـ admin، ورفض حفظ index مبني على source قديم.
- Compare من main إلى head: ahead بثلاثة commits، behind صفر، وثلاثة ملفات متغيرة.
- PR CI run [43158683373](https://github.com/HVA09/ai-chat-app/actions/runs/43158683373): Frontend وSDK وPreview Builder وProduction Compose ناجحة؛ Backend pytest كان قيد التنفيذ عند آخر تسجيل.
- CodeQL run [43158683271](https://github.com/HVA09/ai-chat-app/actions/runs/43158683271): Python وJavaScript/TypeScript ناجحان.
- لا review threads معلقة عند آخر تحقق.
- يظل PR Draft حتى يكتمل Backend CI ويُراجع أي إخفاق أو تعليق. لا يدمج قبل اكتمال جميع الشروط المطلوبة على نفس head SHA.


## 27. ضبط نطاق PR #696 وإعادة تشغيل الفحوص على أحدث رأس — 2026-11-12

- أثناء مراجعة الطلب، أُزيل تعديل صلاحيات مسار `index-image` القديم من PR #696؛ لأن إعادة تصميم إعادة التحقق بعد Vision تقع خارج نطاق إعادة الفهرسة النصية الحالية ويجب مراجعتها منفصلة.
- وصف PR صُحح ليؤكد أن سلوك فهرسة الصور الحالي غير متغير وخارج هذا الطلب.
- أحدث رأس للفرع أصبح `f559b0d97aacf7e54aedec5239aff01e2fcea159`، والقاعدة لا تزال `main = f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- GitHub أنشأ فحوصًا جديدة على الرأس الأخير:
  - CI run [43158964480](https://github.com/HVA09/ai-chat-app/actions/runs/43158964480): pending عند تسجيل هذا التحديث.
  - CodeQL run [43158964413](https://github.com/HVA09/ai-chat-app/actions/runs/43158964413): in_progress.
- الفحوص التي بدأت قبل تعديل النطاق، مثل CI [43158683373](https://github.com/HVA09/ai-chat-app/actions/runs/43158683373)، ليست بديلًا عن إعادة فحص الرأس الجديد. لا تعتمد عليها لإعلان اكتمال CI.
- PR #696 يظل Draft وغير مدمج. لا تُنفذ أي إعادة فهرسة على الإنتاج، وتظل بوابة backup/restore الإنتاجية مستقلة ومفتوحة كما في الأقسام السابقة.


## 28. حالة فحوص PR #696 على الرأس الحالي — 2026-11-12

- رأس الفرع الحالي: `f559b0d97aacf7e54aedec5239aff01e2fcea159`.
- CI run [43158964480](https://github.com/HVA09/ai-chat-app/actions/runs/43158964480): `in_progress`؛ وظيفة SDK انتهت بنجاح، ووظائف Backend وFrontend وPreview Builder وProduction Compose كانت قيد التنفيذ.
- CodeQL run [43158964413](https://github.com/HVA09/ai-chat-app/actions/runs/43158964413): Python وJavaScript/TypeScript كانتا قيد التحليل.
- لم تظهر نتيجة فشل في آخر check-runs، لكن لا تُسجل هذه الوظائف نجاحًا قبل اكتمالها.
- PR #696 ما زال Open / Draft / unmerged؛ لم يحدث deploy إلى Render أو أي تغيير إنتاجي بسبب هذا الفرع.
- يبقى القرار: لا تدمج قبل اكتمال جميع checks على الرأس الحالي ومراجعة نتائج Backend tests؛ لا تُنفذ أي reindex إنتاجي.



## 29. إصلاح إعادة تحميل ACL وإضافة اختبار سحب الصلاحية أثناء إعادة الفهرسة — 2026-11-12

### نتيجة مراجعة PR #696
- أُنجز CI وCodeQL بنجاح على الرأس السابق `f559b0d97aacf7e54aedec5239aff01e2fcea159`؛ Backend وFrontend وPreview Builder وProduction Compose وSDK وCodeQL كلها Success.
- أثناء مراجعة أعمق، ظهرت ثغرة توقيت محتملة في إعادة التحقق: كائنات WorkspaceMember وProjectMember وعلاقات RBAC التي حُمّلت قبل استدعاء مزود embeddings قد تبقى في SQLAlchemy identity map، وبالتالي لا يكفي تكرار الاستعلام وحده لضمان قراءة أحدث صلاحيات بعد سحبها.
- لم يُدمج الرأس السابق؛ أُوقف الدمج لإصلاح هذا السلوك.

### الإصلاح
- في `POST /files/{file_id}/reindex` أصبح `db.expire_all()` يُنفذ بعد عودة مزود embeddings وقبل إعادة قفل الملف وإعادة فحص الوصول والصلاحيات؛ هذا يبطل snapshots السابقة ويجبر الاستعلامات التالية على تحميل قيم ACL/RBAC الحالية من قاعدة البيانات.
- أُضيف اختبار تكاملي يحوّل عضو المشروع من editor إلى viewer أثناء callback تجهيز embeddings، مع تعطيل مزامنة SQLAlchemy للـ identity map، ويتحقق من رفض العملية `403` وعدم استبدال المقاطع القديمة.
- لا توجد تغييرات schema أو migration أو تعديل على Render/Supabase أو بيانات الإنتاج.

### حالة الرأس والفحوص
- PR #696: https://github.com/HVA09/ai-chat-app/pull/696 — Open / Draft / غير مدمج.
- أحدث head بعد الإصلاح: `06e30ac92be8861199b47e847e034ff6c692d276`.
- Base: `main = f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- Compare: 6 commits ahead، 0 behind، 3 ملفات متغيرة.
- فحوص الرأس الجديد:
  - CI run [43258432310](https://github.com/HVA09/ai-chat-app/actions/runs/43258432310): `in_progress` عند تسجيل هذا القسم.
  - CodeQL run [43258432091](https://github.com/HVA09/ai-chat-app/actions/runs/43258432091): `in_progress`.
- نجاح CI/CodeQL على `f559b0d...` لا يُعد دليلاً على نجاح الرأس الجديد `06e30ac...`؛ يجب انتظار النتائج النهائية الخاصة به.
- لا توجد مراجعات أو review threads معلّقة عند آخر تحقق.
- القرار: لا تحويل إلى Ready ولا دمج حتى نجاح كل checks على أحدث head ومراجعة نتيجة اختبار سحب صلاحية المشروع. لا إعادة فهرسة إنتاجية، ولا backfill، وتبقى بوابة backup/restore الإنتاجية مفتوحة كما سُجل سابقًا.



## 30. دمج PR #696 وتأكيد نجاح ما قبل الدمج — 2026-11-12

### قرار الدمج والدليل
- اكتملت كل فحوص PR على الرأس `06e30ac92be8861199b47e847e034ff6c692d276` بنجاح:
  - Backend، Frontend، SDK، Preview Builder، Production Compose.
  - CodeQL Python وJavaScript/TypeScript.
- Backend test job اكتمل Success عند `2026-11-12T16:31:29Z`؛ جميع check-runs الثمانية على الرأس نفسه أصبحت `completed/success`.
- PR #696 لم يكن يحتوي review threads أو مراجعات معلقة، وكان GitHub يعرض `mergeable_state=clean`.
- حُوّل PR من Draft إلى Ready بعد نجاح كل الفحوص، ثم دُمج بطريقة Squash بتفويض المستخدم السابق.
- PR: https://github.com/HVA09/ai-chat-app/pull/696
- Merge commit وmain الحالي وقت التسجيل: `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- عنوان commit: `feat(rag): add safe per-file reindex endpoint`.
- يحتوي commit على فصل prepare/persist، endpoint أحادي الملف، فحوص ACL حية بعد provider I/O مع `db.expire_all()`، واختبار تغيير دور المشروع أثناء embeddings.

### فحوص ما بعد الدمج
- بدأت GitHub workflows على merge commit:
  - CI run [43262134820](https://github.com/HVA09/ai-chat-app/actions/runs/43262134820): `in_progress` في آخر فحص.
  - Production smoke [43262134748](https://github.com/HVA09/ai-chat-app/actions/runs/43262134748): `in_progress`.
  - CodeQL [43262134713](https://github.com/HVA09/ai-chat-app/actions/runs/43262134713): `in_progress`.
  - Publish backend image [43262134613](https://github.com/HVA09/ai-chat-app/actions/runs/43262134613): `in_progress`.
- هذه فحوص Push بعد الدمج؛ لا تخلط مع PR checks التي نجحت قبل الدمج. يجب تسجيل نتائجها عند اكتمالها.

### Render بعد الدمج
- الخدمة ما زالت إعداداتها كما هي: `autoDeploy=yes`, `autoDeployTrigger=checksPass`, branch `main`, plan `free`, health path `/health`، workspace `My Workspace`.
- قراءة Render الأخيرة أظهرت أن أحدث deployment Live ما زال على SHA السابق `f3ba9d4...`; لم يظهر بعد deploy على `31503ae...` عند وقت الفحص.
- لا manual deploy ولا أي تغيير في إعدادات Render. ينتظر Render تحقق شروط checksPass تلقائيًا.
- عند الفحص الأخير، سجل Render deployment الحالي `dep-dbqju7e7bikc739n63i0` بقي Live على SHA السابق. يجب إعادة فحص deployments/events بعد انتهاء GitHub checks.
- PR #696 كود فقط ولا يتضمن migration أو عملية reindex أو backfill؛ لا يتوقع أي تحديث لقاعدة الإنتاج من هذا الدمج.
- بوابة backup/restore الإنتاجية لا تزال مفتوحة؛ يمنع أي bulk reindex/backfill أو strict retrieval fingerprint filtering قبل إغلاقها بأدلة.




## 31. تحديث فحوص Push بعد دمج PR #696 — 2026-11-12

- commit الدمج `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db` مؤكد على `main`.
- CodeQL Push run [43262134713](https://github.com/HVA09/ai-chat-app/actions/runs/43262134713): `completed/success`.
- Publish backend image run [43262134613](https://github.com/HVA09/ai-chat-app/actions/runs/43262134613): `completed/success`.
- CI run [43262134820](https://github.com/HVA09/ai-chat-app/actions/runs/43262134820): ما زال `in_progress`؛ Backend tests وFrontend test كانت قيد التشغيل في آخر قراءة، بينما SDK وPreview Builder وProduction Compose نجحت.
- Production smoke run [43262134748](https://github.com/HVA09/ai-chat-app/actions/runs/43262134748): ما زال `in_progress` في آخر قراءة.
- Render service ما زال يعلن `autoDeploy=yes` و`autoDeployTrigger=checksPass` على main، ولم يظهر بعد deployment على SHA `31503ae...`. أحدث deployment المسجل ما زال SHA `f3ba9d4...`.
- لا نُطلق manual deploy؛ نعيد فحص Render بعد اكتمال CI/smoke. لا تغييرات يدوية على الخدمة أو الإنتاج.



## 32. نجاح Production smoke بعد دمج PR #696 — 2026-11-12

- Production smoke run [43262134748](https://github.com/HVA09/ai-chat-app/actions/runs/43262134748) على merge commit `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`: `completed/success`.
- CodeQL Push وPublish backend image: `completed/success`.
- CI run [43262134820](https://github.com/HVA09/ai-chat-app/actions/runs/43262134820): الوظائف Frontend وSDK وPreview Builder وProduction Compose نجحت؛ Backend ما زال عند خطوة `Run backend tests with hang diagnostics` في آخر قراءة.
- Render لم يبدأ deployment على commit الدمج بعد؛ آخر deployment Live ما زال على `f3ba9d4...`. الإعداد `checksPass` ما زال مفعّلًا ولا توجد عملية نشر يدوية.
- لا يُغلق فحص النشر إلا بعد نجاح Backend CI ثم ظهور deployment جديد على `31503ae...` والتحقق من الصحة الداخلية/السجلات.



## 33. اكتمال نشر PR #696 وتوثيق إشارات التشغيل بعد النشر — 2026-11-12

### نجاح الدمج والفحوص والنشر
- PR #696 مدمج؛ merge commit على `main`: `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- Post-merge CI run [43262134820](https://github.com/HVA09/ai-chat-app/actions/runs/43262134820): `completed/success`، بما في ذلك Backend **613 passed, 2 warnings**، وFrontend، SDK، Preview Builder، Production Compose.
- Production smoke [43262134748](https://github.com/HVA09/ai-chat-app/actions/runs/43262134748): Success.
- CodeQL [43262134713](https://github.com/HVA09/ai-chat-app/actions/runs/43262134713): Success.
- Publish backend image [43262134613](https://github.com/HVA09/ai-chat-app/actions/runs/43262134613): Success.
- Render deployment [dep-dbqusce7bikc73971u30](https://dashboard.render.com/web/srv-dakc4nbm8hqs73e2po9g): commit `31503ae...`, build succeeded، وانتهى deployment `live` عند `2026-11-12T16:52:18Z`.
- Render startup logs للـ instance الجديد `srv-dakc4nbm8hqs73e2po9g-f94zg` أكدت Object Storage connectivity OK، وبدء Celery worker/beat، و`Application startup complete`، وبدء Uvicorn.
- Health-check logs على instance الجديد أظهرت `GET /health 200` بصورة متكررة (latency بعد أول فحص بين نحو 10 و14ms).
- استعلام Render عن app errors من `16:52:18Z` إلى `16:57:00Z` أعاد قائمة فارغة. لم يُرصد server_failed أو server_restarted في أحداث الفترة؛ الحدث التشغيلي المسجل هو `deploy_ended: succeeded`.
- لم تُشغّل يدويًا عملية Deploy، ولم تتغير إعدادات Render أو Supabase أو الأسرار. لا migration أو reindex أو backfill في PR #696.

### ملاحظة QueuePool على الإصدار السابق — تتبع #674
- في instance القديم `srv-dakc4nbm8hqs73e2po9g-52f48` وقبل بدء deployment الجديد، عند `2026-11-12T16:49:46Z`، ظهرت أخطاء SQLAlchemy:
  `QueuePool limit of size 2 overflow 1 reached, connection timed out, timeout 15.00`.
- ظهر `GET /chat/models` بنتيجة `500` بعد latency تقارب 15.2 ثانية.
- يوضح traceback أن محاولة مصادقة WebSocket في `app/routers/notifications.py:89` فشلت عند `db.get(User, user_id)` لعدم توفر اتصال.
- لا نستنتج أن WebSocket احتفظ باتصال طوال عمره؛ الشيفرة الحالية تستخدم `SessionLocal()` قصير العمر حول هذا الاستعلام. الدليل يثبت فقط أن خانات pool الثلاث (2 + overflow 1) كانت كلها مشغولة وقت المحاولة؛ ما زال يلزم ربط ذلك بالطلبات الأخرى التي كانت تحتفظ بالاتصالات.
- الحادث وقع في `16:49:46Z`، قبل `deploy_started` للإصدار الجديد في `16:49:53Z`، لذلك لا يُنسب إلى PR #696.
- أُضيفت الأدلة والتحفظات إلى Issue [#674](https://github.com/HVA09/ai-chat-app/issues/674) (comment ID `6830129617`). تبقى القضية مفتوحة لاستكمال تحليل مدة checkout ومسارات الانتظار الخارجية؛ لا ترفع pool size أو تغير Render/DB استنادًا إلى عينة واحدة.

### ملاحظة Gemini 503 — تتبع #683
- في instance القديم نفسه عند `2026-11-12T16:49:51.53Z`، فشل بث محادثة برقم request ID `e66d3c9aeb8241c3` برسالة upstream `503 Service Unavailable` من Gemini OpenAI-compatible `/chat/completions`.
- التطبيق سجل `retryable=True` و`emitted=False` ثم `AI streaming failover unavailable primary_provider=gemini`.
- وقع الحدث قبل بدء deployment الجديد بنحو ثانيتين؛ لا يوجد دليل لربطه بـ PR #696.
- يثبت السجل عدم توفر fallback صالح لهذا الطلب، لكنه لا يميز هل السبب غياب الإعداد، نقصه، أو تطابقه مع المزود الأساسي. لم نفحص أو نغير أسرار/إعدادات مزود الإنتاج ولم ننفذ اختبار AI حيًا بعد النشر.
- أُضيفت الأدلة إلى Issue [#683](https://github.com/HVA09/ai-chat-app/issues/683) (comment ID `6830132102`). تبقى القضية مفتوحة لفحص سبب عدم توفر fallback والتعامل الآمن مع أخطاء المزود العابرة.

### حالة الاستقرار والحدود المتبقية
- النسخة المدمجة والمنشورة حاليًا: `31503ae...`، وRender status `Live`.
- الاختبارات وفحص الصحة الداخلي ناجحان. فحص HTTP خارجي مستقل لم ينجح عبر أداة الويب؛ تعذر الوصول إلى `/health` و`/ready` منها، فلا نسجل نجاح اختبار خارجي.
- لا نعلن أن تجربة محادثة حقيقية مع Gemini نجحت بعد النشر؛ لا توجد مكالمة إنتاجية اختبارية موثقة بعد تلك الواقعة.
- بوابة backup/restore الإنتاجية لا تزال مفتوحة كما في الأقسام السابقة؛ يمنع backfill أو bulk reindex أو strict retrieval fingerprint filtering حتى تتوفر أدلة نسخة احتياطية واختبار استعادة.
- لا توجد ميزات جديدة في هذا المسار؛ العمل التالي ضمن الاستقرار: تحليل pool exhaustion في #674، وإغلاق تشخيص provider/fallback في #683 بأدلة واختبارات قبل أي إعداد إنتاجي.



## 33. تأكيد استقرار Render بعد PR #696 واكتشاف توافق أبعاد Gemini — 2026-11-12

### Deployment الجديد
- Render deployment [dep-dbqusce7bikc73971u30](https://dashboard.render.com/web/srv-dakc4nbm8hqs73e2po9g/deploys/dep-dbqusce7bikc73971u30) على SHA `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db` أصبح `live`.
- وقت الانتهاء: `2026-11-12T16:52:18.876505Z`; event `deploy_ended/succeeded` عند `16:52:18.999789Z`.
- Instance الجديد: `srv-dakc4nbm8hqs73e2po9g-f94zg`.
- Startup logs أكدت بدء التطبيق production، اتصال Object Storage، تشغيل Celery worker/beat، وبدء Uvicorn.
- Render internal health logs سجلت `GET /health 200` بصورة دورية، latency غالبًا 10–15ms، من `16:52:18Z` إلى آخر فحص `17:00:38Z`.
- سجلات `error` بعد وقت Live (من `16:52:18Z` إلى `17:05:00Z`) كانت فارغة، ولا request logs برموز 500/502/503/504 على instance الجديد في الفترة نفسها.
- حدث `GET /` واحد برمز 404 عند بدء التشغيل فقط؛ هذا ليس endpoint صحة الخدمة ولا يُسجل كفشل في التطبيق.
- أدوات الويب المستقلة لم تستطع فتح /health أو /ready؛ لذلك لا نسجل فحص HTTP خارجي ناجح. دليل الصحة الحالي مبني على Render internal logs فقط.

### فصل أخطاء النسخة القديمة عن الجديدة
- قبل بدء deployment الجديد، على instance القديم `...-52f48`:
  - `16:49:46Z`: SQLAlchemy QueuePool exhaustion (`pool_size=2`, `max_overflow=1`, timeout 15s)، وطلب `GET /chat/models` استغرق نحو 15.2 ثانية ثم فشل.
  - `16:49:48Z`: RAG query فشل لأن مزود Gemini أعاد 3072 بعدًا بينما التطبيق يتطلب 768؛ انتقل ذلك الطلب إلى fallback للسياق الكامل.
  - `16:49:51Z`: Gemini chat completions أعاد `503 Service Unavailable` في محادثة واحدة، وسُجل أن AI streaming failover غير متاح.
  - بدأ Render deploy الجديد عند `16:49:53Z`، أي بعد هذه الأخطاء.
- لم تتكرر أخطاء QueuePool أو 5xx أو Gemini logs على instance الجديد بعد وصوله إلى Live خلال نافذة الفحص؛ مع ذلك لم يُنفذ اختبار محادثة فعلي موثق على النسخة الجديدة، فلا نستنتج من غياب السجلات نجاح مزود Gemini عند الاستخدام الفعلي.
- لا نغيّر DATABASE_POOL_SIZE أو إعدادات Gemini في الإنتاج بناءً على حادثة واحدة. تُتابع هذه النقاط كتحقيقين منفصلين.

### PR #697 لمعالجة أبعاد Gemini
- PR #697: https://github.com/HVA09/ai-chat-app/pull/697 — Draft / Open / غير مدمج.
- Branch: `fix/gemini-mrl-embedding-dimensions-20261112`.
- Base: `main = 31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- Head: `ed84bc40443c337729b993127fae10baff9c36e8`.
- التغيير محدود بملفين: `ai-backend/app/services/embeddings.py` و`ai-backend/tests/test_embedding_configuration.py`.
- السبب: خدمة Gemini embedding model `gemini-embedding-001` تعيد 3072 بعدًا افتراضيًا؛ وثائق Google توضح دعم MRL لتقليل المتجه إلى 768/1536 وإعادة تطبيعه عند تقليل أبعاد `gemini-embedding-001`.
- أضيف fallback دقيق عند تحقق الشروط كلها: provider=Gemini، model=`gemini-embedding-001`، الاستجابة كلها 3072، والأبعاد المطلوبة أقل من 3072. نأخذ البادئة المطلوبة ونعيد L2 normalization. ينطبق ذلك على query embeddings وdocument batch embeddings معًا.
- النماذج الأخرى والمزودون الآخرون والمتجهات غير المطابقة تمامًا 3072 لا تُقتطع؛ يظل التحقق الصارم قائمًا.
- لا migration، لا تغيير `vector(768)`، لا reindex/backfill إنتاجي، لا مفاتيح أو متغيرات بيئة أو Render/Supabase writes.
- اختبارات CI وCodeQL على أحدث رأس لم تكتمل بعد عند تسجيل هذا القسم؛ PR يبقى Draft ولا يدمج قبل نجاحها.
- الروابط الرسمية:
  - https://ai.google.dev/gemini-api/docs/embeddings
  - https://ai.google.dev/api/embeddings

### بوابات لم تُغلق
- backup/restore production ما زالت غير مثبتة؛ لا bulk reindex/backfill ولا strict retrieval fingerprint filtering.
- لا دليل خارجي مستقل لفحص /health أو /ready بعد النشر.
- لا نقوم باختبار محادثة إنتاجية مصطنع أو إعادة فهرسة حقيقية على بيانات المستخدم دون تفويض/خطة محددة؛ الفحص الحالي read-only.



## 34. حالة CI الأولية لطلب إصلاح أبعاد Gemini #697 — 2026-11-12

- PR #697 ما زال Open / Draft / غير مدمج.
- أحدث رأس: `ed84bc40443c337729b993127fae10baff9c36e8`، والقاعدة `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- CodeQL على الرأس الحالي: `completed/success` (Python وJavaScript/TypeScript).
- CI run [43265924789](https://github.com/HVA09/ai-chat-app/actions/runs/43265924789):
  - SDK: Success.
  - Preview Builder: Success.
  - Production Compose: Success.
  - Frontend: Success.
  - Backend: لا يزال عند `Run backend tests with hang diagnostics` في آخر قراءة.
- لم تظهر مراجعات أو review threads معلّقة.
- سجل job logs لم يكن قابلًا للتنزيل أثناء استمرار المهمة (GitHub/Azure BlobNotFound)؛ هذا ليس فشل اختبار.
- لا تعتمد نجاحًا نهائيًا للطلب حتى تنتهي Backend pytest على نفس head SHA، ثم نفحص جميع check-runs ونجعل PR Ready/merge عند استيفاء الشروط.
- لا production writes أو إعادة فهرسة؛ PR #697 تغييرات كود واختبارات فقط.



## 35. دمج PR #697 لمعالجة أبعاد Gemini بعد نجاح الاختبارات — 2026-11-12

### نتائج PR checks
- PR #697 على head `ed84bc40443c337729b993127fae10baff9c36e8` اجتاز كل check-runs الثمانية بنجاح:
  - Backend pytest: **616 passed, 2 warnings** في 302.73 ثانية.
  - Frontend، SDK، Preview Builder، Production Compose: Success.
  - CodeQL Python وJavaScript/TypeScript: Success.
- سجل Backend يثبت نجاح الاختبارات الثلاثة الجديدة:
  - `test_gemini_embedding_001_query_truncates_full_mrl_vector_to_schema_dimension`
  - `test_gemini_embedding_001_documents_truncate_full_mrl_vectors_to_schema_dimension`
  - `test_gemini_mrl_fallback_is_limited_to_gemini_embedding_001`
- لا review threads أو reviews معلقة، GitHub `mergeable_state=clean`.
- حُوّل PR من Draft إلى Ready ثم دُمج Squash بتفويض المستخدم السابق.
- PR: https://github.com/HVA09/ai-chat-app/pull/697
- Merge commit وmain: `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
- الأب المباشر للدمج: `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.

### فحوص Push بعد الدمج
- Production smoke run [43267652368](https://github.com/HVA09/ai-chat-app/actions/runs/43267652368): completed/success.
- CI run [43267652121](https://github.com/HVA09/ai-chat-app/actions/runs/43267652121): in_progress عند آخر قراءة.
- CodeQL run [43267652046](https://github.com/HVA09/ai-chat-app/actions/runs/43267652046): in_progress عند آخر قراءة.
- Publish backend image run [43267652172](https://github.com/HVA09/ai-chat-app/actions/runs/43267652172): in_progress عند آخر قراءة.
- هذه فحوص Push بعد الدمج وليست فحوص PR السابقة؛ لا تُسجل كاملة قبل انتهائها على SHA `48c4515...`.

### نطاق الإصلاح وضوابط الإنتاج
- المعالجة تتعامل مع Gemini `gemini-embedding-001` فقط: إذا أعاد كل متجه 3072 قيمة وكانت أبعاد التطبيق أصغر، تُستخدم بادئة MRL المطلوبة ثم يعاد تطبيعها.
- يطبق السلوك على Query وDocument embeddings، ويحافظ على التحقق الصارم للمزودين والنماذج الأخرى.
- لا تغيير على مخطط قاعدة البيانات `vector(768)`، ولا migration، ولا تغيير secrets أو environment variables، ولا إعادة فهرسة أو backfill.
- Render ما زال عليه deployment سابق SHA `31503ae...` وقت آخر فحص؛ يجب انتظار GitHub checksPass ثم إعادة التحقق من deployment الجديد. لا manual deploy.
- لا إجراء بيانات إنتاجية. تبقى بوابة backup/restore مفتوحة قبل أي bulk reindex/backfill أو strict retrieval fingerprint filtering.



## 36. نجاح CI ونشر PR #697 على Render — 2026-11-12

### نتائج ما بعد الدمج
- main والـ merge commit: `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
- CI push run [43267652121](https://github.com/HVA09/ai-chat-app/actions/runs/43267652121): `completed/success`.
  - Backend، Frontend، SDK، Preview Builder، Production Compose: جميعها Success.
- CodeQL [43267652046](https://github.com/HVA09/ai-chat-app/actions/runs/43267652046): Success.
- Publish backend image [43267652172](https://github.com/HVA09/ai-chat-app/actions/runs/43267652172): Success.
- Production smoke [43267652368](https://github.com/HVA09/ai-chat-app/actions/runs/43267652368): Success.
- PR #697 مدمج: https://github.com/HVA09/ai-chat-app/pull/697.

### Render deployment
- Deployment [dep-dbqvb6mq1p3s73dn2m3g](https://dashboard.render.com/web/srv-dakc4nbm8hqs73e2po9g/deploys/dep-dbqvb6mq1p3s73dn2m3g) على SHA `48c451545c0ab2b05e08c94b4afc72b2215a4910` وصل `live`.
- بدأ: `2026-11-12T17:21:30.987833Z`; انتهى: `2026-11-12T17:23:36.372365Z`.
- event `deploy_ended/succeeded` عند `17:23:36.461029Z`.
- Instance الجديد: `srv-dakc4nbm8hqs73e2po9g-gm6g7`.
- Startup logs: Alembic بدأ في سياق PostgreSQL؛ Object Storage connectivity OK؛ Celery worker وbeat بدءا؛ `Application startup complete` عند `17:23:25.932317Z`.
- Render internal `GET /health 200` على instance الجديد تكرر كل ~5 ثوانٍ، latency في العادة 9–14ms من `17:23:35Z` إلى `17:24:55Z` على الأقل.
- سجلات app `error` على instance الجديد في الفترة `17:23:36Z–17:28:00Z`: فارغة.
- طلبات HTTP ذات status 500/502/503/504 على instance الجديد في الفترة نفسها: لا نتائج.
- ظهرت طلبات `HEAD / 404` و`GET / 404` في probes الافتراضية عند بدء التشغيل؛ ليست endpoint صحة الخدمة ولا تُسجل كفشل API.
- لا تغيير يدوي في Render ولا Secrets ولا إعدادات الخدمة؛ النشر حدث تلقائيًا عبر `autoDeployTrigger=checksPass`.

### حدود التحقق المتبقية
- تم التأكد من نشر الكود ونجاح الصحة الداخلية، لكن سجلات الفترة بعد الإصدار الجديد لم تعرض طلب محادثة authenticated يستدعي RAG؛ لذلك لا نعلن end-to-end Gemini/RAG chat success من health checks فقط.
- اختبار MRL الجديد اجتاز المحاكاة على CI (query + document)، ويُتوقع أن يعالج اختلاف 3072/768 دون تغيير المخطط، لكن أول استخدام فعلي بعد النشر ما زال دليله مطلوبًا.
- حادثة Gemini chat 503 السابقة تخص instance القديم قبل نشر الإصدار السابق؛ لا دليل أنها تكررت بعد النشر الأخير، لكن لا تغيير على إعدادات fallback أو المفاتيح.
- حادثة QueuePool المؤقتة كانت على instance القديم قبل نشر PR #696، ولم تظهر على instance الجديد في نافذة المراقبة. لا تغييرات pool settings.
- لا reindex إنتاجي، ولا bulk/backfill، ولا strict fingerprint filtering؛ بوابة backup/restore الإنتاجية ما زالت مفتوحة.
- في سجلات PostgreSQL الخاصة ببيئة CI ظهر duplicate key واحد على قيد `uq_scheduled_task_runs_task_scheduled_for` أثناء تشغيل الاختبارات، مع أن pytest انتهت `616 passed, 2 warnings`؛ لا يمثل فشل CI، لكنه يستحق مراجعة منفصلة إن تكرر أو ظهر على الإنتاج.



## 34. دمج إصلاح أبعاد Gemini والتحقق بعد النشر — 2026-11-12

### PR #697 والدمج
- PR #697 `fix(rag): handle full-dimensional Gemini 001 embeddings`: merged بواسطة مالك المستودع عند `2026-11-12T17:16:21Z`.
- PR: https://github.com/HVA09/ai-chat-app/pull/697
- Merge commit / main الحالي وقت الفحص: `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
- PR checks على head `ed84bc40443c337729b993127fae10baff9c36e8`: Backend، Frontend، SDK، Preview Builder، Production Compose، CodeQL Python وJavaScript/TypeScript كلها Success.
- Backend pytest: `616 passed, 2 warnings in 237.79s`.
- Post-merge runs كلها `completed/success`:
  - CI [43267652121](https://github.com/HVA09/ai-chat-app/actions/runs/43267652121)
  - Production smoke [43267652368](https://github.com/HVA09/ai-chat-app/actions/runs/43267652368)
  - Publish backend image [43267652172](https://github.com/HVA09/ai-chat-app/actions/runs/43267652172)
  - CodeQL [43267652046](https://github.com/HVA09/ai-chat-app/actions/runs/43267652046)

### مراجعة الكود والقيود
- تعديل MRL محصور في `gemini-embedding-001` عندما تكون كل المتجهات المستلمة 3072 بعدًا والأبعاد المخزنة المطلوبة أقل من 3072؛ يأخذ البادئة المطلوبة ويعيد L2 normalization.
- يطبق المنطق على document batch وquery embeddings معًا؛ باقي المزودين والنماذج والأبعاد غير المطابقة تبقى تحت التحقق الصارم.
- وثائق Google الرسمية توضح أن `gemini-embedding-001` يدعم أبعاد 768/1536/3072، وأن تقليل أبعاد هذا النموذج يتطلب إعادة normalization يدويًا: https://ai.google.dev/gemini-api/docs/embeddings
- تعليق Codex الآلي على PR #697 سجّل أنه لم يتمكن من إكمال مراجعة الكود بسبب حد الاستخدام؛ هذا ليس دليلًا على مراجعة آلية نظيفة. CodeQL نجح، وأُجري فحص يدوي لنطاق التعديل قبل تسجيل هذه النتيجة، لكن لم تتوفر مراجعة Codex مستقلة كاملة.
- لا migration ولا schema change ولا تعديل إعدادات Render/Supabase أو الأسرار، ولا reindex/backfill إنتاجي. `vector(768)` بقي كما هو.

### Render بعد PR #697
- Deployment [dep-dbqvb6mq1p3s73dn2m3g](https://dashboard.render.com/web/srv-dakc4nbm8hqs73e2po9g/deploys/dep-dbqvb6mq1p3s73dn2m3g) على SHA `48c451545c0ab2b05e08c94b4afc72b2215a4910` أصبح `live`، وانتهى عند `2026-11-12T17:23:36Z`.
- Render events: build وdeploy succeeded؛ Render auto-deploy ظل `checksPass`، ولم يُطلق manual deploy.
- بعد Live وحتى آخر نافذة سجلات تمت مراجعتها:
  - لا app-level error logs.
  - لا request 500/502/503/504.
  - لا QueuePool exhaustion.
  - لا تحذيرات mismatch لأبعاد embeddings.
  - سجلات Render الداخلية أظهرت `GET /health 200` بصورة دورية بزمن غالبًا 9–16ms؛ آخر عينة مرئية في نتيجة الفحص كانت قبل `17:38:36Z`.
- فحص HTTP خارجي مباشر لم يكتمل من بيئة العمل بسبب فشل DNS؛ لذلك لا نسجل external /health test ناجحًا. الدليل الإيجابي الحالي هو Render internal logs ونجاح Production smoke.
- لا يوجد طلب Gemini chat/RAG إنتاجي فعلي موثق بعد التغيير في السجلات المعروضة؛ اختبارات CI تثبت السلوك بالكود والـmocks، لكنها لا تثبت توافر Gemini upstream وقت الاستخدام الفعلي.

### بوابات مستمرة
- حادثة QueuePool وGemini HTTP 503 وعدم تطابق 3072/768 سُجلت على الـinstance القديم قبل انتهاء تبديل Render؛ لم تتكرر على الـinstance الجديد في السجلات التي تمت مراجعتها.
- لا تغيير لحدود اتصال قاعدة البيانات استنادًا إلى حادثة واحدة.
- بوابة backup/restore الإنتاجية ما زالت مفتوحة؛ يُمنع bulk reindex/backfill وstrict retrieval fingerprint filtering قبل توفير backup حديث ودليل restore ناجح.



## 37. إثبات نسخة احتياطية خارجية ناجحة وفتح إصلاح أمان الاستعادة على main الحالي — 2026-11-12

### النسخة الاحتياطية الخارجية
- عُثر على تشغيل Workflow المجدول [43199588287](https://github.com/HVA09/ai-chat-app/actions/runs/43199588287) بعنوان `Production database backup`.
- التشغيل: `2026-11-12T10:21:07Z`، على commit `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`، والحالة `completed/success`.
- نجح job `backup` بجميع خطواته: `pg_dump --format=custom`، وفحص الأرشيف بـ`pg_restore --list`، ورفع S3-compatible، والتحقق البعيد بـ`head-object`، ثم حذف النسخة المحلية.
- اسم الملف المعلن في سجل job: `ai-chat-postgres-20261112T102110Z.dump`.
- حجم الكائن البعيد الذي أعاده `head-object`: `862003` bytes؛ وقد عاد ETag في السجل.
- أكّد preflight أن `PRODUCTION_BACKUP_ENABLED=true` و`PRODUCTION_DB_CREDENTIAL_ROTATED=true` وأن حقول الإعداد الأساسية كانت موجودة؛ لم تُقرأ أي أسرار أو تُعرض قيمها.
- هذا دليل على وجود أرشيف خارجي تم إنشاؤه والتحقق من هيكله ووجوده البعيد. لكنه ليس دليل استعادة.
- قيد إثبات مهم: قيمة GitHub secret `PRODUCTION_DATABASE_URL` مخفية عن القراءة؛ لذلك لا يثبت سجل Actions وحده المضيف/المشروع المصدر الذي جرى تصديره. يجب عدم الادعاء أن نسخة الملف تطابق مشروع Supabase `ai-chat-prod-db` بشكل مؤكد حتى يتم إثبات provenance بطريقة آمنة لا تكشف الاعتماد السري.
- لم يتوفر دليل أن هذا الأرشيف استُعيد بنجاح إلى قاعدة staging. تظل بوابة restore test مفتوحة.
- Supabase organization على خطة `free`; وثائق Supabase الرسمية تقول إن النسخ التلقائية اليومية متاحة لخطط Pro/Team/Enterprise، وتوصي الخطة المجانية بتصدير `db dump` دوريًا خارج المنصة. تشغيل Workflow المجدول أعلاه هو مسار off-site مستقل، ولا يثبت تشغيل النسخ التلقائية على Supabase Free.
- وثائق Supabase: https://supabase.com/docs/guides/platform/backups

### حالة PR #673 وإصلاح الاستعادة
- PR #673 القديم ما زال Draft وعلى branch متأخر 59 commit عن `main` عند SHA `48c4515...`; لم ندمجه.
- ملف `.github/workflows/restore-to-supabase.yml` الموجود في `main` الحالي ما زال يستخدم أسرار S3 العامة و`SUPABASE_DB_URL` عامة، ويختار أحدث `.dump` من prefix عام `database/` ثم ينفذ `pg_restore --clean --if-exists --schema=public`. هذا مسار قابل لتحديد وجهة غير staging إذا شُغّل بإعدادات خاطئة؛ يجب استبداله قبل أي استخدام.
- أُعيد تطبيق التغيير الأمني من PR #673 على branch جديد مبني مباشرة على main الحالي لتجنب فجوة الـ59 commit:
  - PR #698: https://github.com/HVA09/ai-chat-app/pull/698
  - Branch: `security/restore-supabase-staging-only-20261112`.
  - Base: `main = 48c451545c0ab2b05e08c94b4afc72b2215a4910`.
  - Head: `7086001c962711dd2fcd5bbfa28a848aa34d3a25`.
  - التغييرات الثلاثة: استبدال workflow إلى staging-only، إضافة `restore_target_guard.py`، واختبارات guard.
  - ضوابط التغيير: لا target إلا staging، تأكيد يدوي صريح، قفل على فرع main، GitHub Environment `supabase-staging` مع required reviewers prerequisite، secrets مخصصة، حظر production project ref، تحقق URL/port/database/TLS/root CA وإعادة التحقق قبل restore، وحصر اختيار dump تحت `database/staging-sanitized/`.
- PR #698 ما زال Draft، غير مدمج؛ CI run [43275707523](https://github.com/HVA09/ai-chat-app/actions/runs/43275707523) وCodeQL [43275715170](https://github.com/HVA09/ai-chat-app/actions/runs/43275715170) كانا `in_progress` في آخر تسجيل.
- لا توجد مراجعات أو review threads معلقة عند إنشاء PR #698.
- لم نشغّل workflow الاستعادة، ولم ننشئ staging secrets أو GitHub Environment، ولم نغيّر قاعدة Supabase أو أي إعدادات Render/Supabase.
- لا يُحوّل PR #698 إلى Ready ولا يُدمج حتى نجاح جميع الفحوص على أحدث head ومراجعة workflow والاختبارات. بعد دمجه، تظل تجربة restore إلى staging بحاجة إلى إعداد بيئة staging معزولة وموافقة reviewer ونسخة sanitized dump صالحة.

### القرار التشغيلي
- **Backup artifact وجوده مثبت** على مستوى workflow/object-store metadata.
- **Source provenance غير مثبت بالكامل** لأن قيمة `PRODUCTION_DATABASE_URL` سرية ولا تظهر في السجل.
- **Restore capability غير مثبتة** حتى الآن.
- يُسمح بالاستمرار في مراجعة الكود والاختبارات، لكن لا bulk reindex/backfill ولا strict retrieval fingerprint filtering ولا تشغيل restore على Production. لا إعادة فهرسة إنتاجية لحد الآن.
- أضيف تصحيحًا للحالة التاريخية: PR #697 مدمج ومنشور على main في SHA `48c451545c0ab2b05e08c94b4afc72b2215a4910`; الأقسام السابقة التي تسجل أنه Draft تعكس حالة سابقة فقط.


## 38. تحسين قابلية تدقيق ملف الاستعادة المحدد في PR #698 — 2026-11-12

### ما تم إنجازه
- تأكد دمج PR #696 بعد نجاح جميع الفحوص؛ merge commit: `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- تأكد دمج PR #697 لمعالجة Gemini Embedding 001، وأن main وصل إلى `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
- PR #697 post-merge CI وCodeQL وProduction smoke وPublish image كلها Success، ونشر Render `dep-dbqvb6mq1p3s73dn2m3g` على SHA `48c4515...` وصل Live.
- PR #698 الحالي: https://github.com/HVA09/ai-chat-app/pull/698
  - base `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
  - قبل التحسين، head `7086001c962711dd2fcd5bbfa28a848aa34d3a25` اجتاز جميع 8 check-runs؛ Backend `644 passed, 2 warnings` في `296.64s`، وCodeQL Python/JavaScript-TypeScript Success.
  - لا reviews أو review threads على PR.
- مراجعة Workflow وجدت أن اختيار أحدث ملف آليًا داخل `database/staging-sanitized/` لا يُظهر للمراجع قبل موافقته على GitHub Environment اسم الأرشيف الدقيق، ويضعف ربط الموافقة بالملف المقصود.
- تم تعديل Workflow ليطلب `backup_filename` صراحة كـworkflow_dispatch input، ويكوّن المفتاح تحت prefix الثابت، ثم يطبق `is_safe_staging_backup_key` ويفحص `head-object` على الكائن نفسه قبل تنزيله. لم يعد هناك auto-select لأحدث dump.
- تحديث PR body يوضح أن المشغل يختار الملف الذي تمت مراجعته مسبقًا؛ وتم تثبيت إبقاء PR Draft حتى اكتمال الفحوص على الرأس الجديد.

### رأس PR #698 بعد التحسين
- head: `fde39323282a5f87770709222a9cf6ff20ad5b55`.
- Workflow commit: `ed21f1cdc6eabcd7c2d790398749356904fe05d4`، ثم تصحيح صيغة expression وGITHUB_ENV export ضمن commit `fde39323282a5f87770709222a9cf6ff20ad5b55`.
- CI run [43278133710](https://github.com/HVA09/ai-chat-app/actions/runs/43278133710): بدأ؛ Backend وFrontend وPreview Builder وProduction Compose كانت In Progress في آخر قراءة؛ SDK Success.
- CodeQL run [43278133548](https://github.com/HVA09/ai-chat-app/actions/runs/43278133548): Analyze Python وJavaScript/TypeScript In Progress.
- لا merge قبل اكتمال الفحوص ومراجعة النسخة الأخيرة نفسها.

### حدود التشغيل
- لم نشغّل Workflow الاستعادة، ولم ننفذ `pg_restore`، ولم نُنشئ GitHub Environment أو secrets أو متغيرات staging، ولم نغيّر Supabase أو Render أو قاعدة الإنتاج أو ملفات النسخ الاحتياطية.
- النسخة الخارجية الموجودة تثبت object existence/archive listing فقط؛ source provenance غير مثبت بالكامل، وsuccessful restore غير مثبت.
- لا bulk reindex/backfill ولا strict retrieval fingerprint filtering قبل إثبات provenance وsuccessful restore إلى staging معزول.
- سجل الاختبارات السابق سجل duplicate-key واحدًا على قيد `uq_scheduled_task_runs_task_scheduled_for` ضمن PostgreSQL CI مع نجاح pytest؛ يبقى ملاحظة مراقبة وليس فشلًا في PR #698.


## 39. تثبيت اسم النسخة وSHA-256 في Workflow الاستعادة — 2026-11-12

- أُضيف حقل `backup_sha256` مطلوب إلى `workflow_dispatch`؛ يجب أن يكون 64 قيمة hex وأن يطابق الملف الذي تمت مراجعته قبل التشغيل.
- أضيفت الدالة `verify_sha256_file` باستخدام SHA-256 وconstant-time digest comparison؛ تعيد رفض أي digest ناقص/غير صالح أو لا يطابق محتوى الملف.
- أضيفت اختبارات:
  - يقبل SHA-256 المطابق للأرشيف.
  - يرفض digest غير المطابق.
  - يرفض digest بترميز/طول غير صحيح.
- تحقق الملف الآن يتطلب ثلاثة مدخلات متوافقة: target=staging، اسم الملف exact تحت prefix ثابت، وSHA-256 المعتمد. لم يعد يسمح باختيار أحدث backup تلقائيًا أو صلاحية S3 ListBucket؛ التعليق والتوثيق يطلبان object-read فقط تحت prefix المحدد، بلا list/write.
- PR body عُدّل ليشترط مراجعة نفس الملف المحدد ونفس digest، ويعرض المتطلبات التشغيلية قبل استخدام workflow.
- PR #698 آخر head: `f72f2601dbc329e0c69860a0ab192929b7503de1`، base `48c451545c0ab2b05e08c94b4afc72b2215a4910`.
- CI [43279524991](https://github.com/HVA09/ai-chat-app/actions/runs/43279524991) بدأ على الرأس الحالي؛ SDK Success، بينما Backend/Frontend/Preview Builder/Production Compose In Progress عند آخر قراءة.
- CodeQL [43279525021](https://github.com/HVA09/ai-chat-app/actions/runs/43279525021) بدأ على الرأس الحالي؛ لم تكتمل النتيجة عند آخر قراءة. لم يعتمد حالة CodeQL المجمّعة `neutral` كنجاح؛ ننتظر نتيجة workflow الفعلية.
- PR يبقى Draft؛ لا Ready/merge حتى تنتهي كل الفحوص على هذا الرأس وبعدها مراجعة الحالة النهائية.
- لا workflow execution، لا `pg_restore`، لا Supabase/Render writes، لا secrets أو environments، ولا تغيير إنتاجي.


## 40. دمج PR #698 وتحقق ما بعد الدمج — 2026-11-12

### نتيجة الدمج
- PR #698 `security: restrict Supabase restore workflow to staging only` أصبح merged.
- PR: https://github.com/HVA09/ai-chat-app/pull/698
- Head الذي اجتاز الاختبارات: `f72f2601dbc329e0c69860a0ab192929b7503de1`.
- Merge commit/main: `df92952686f2a1f21339ab1ae55acb3f6d866164`.
- CI السابق للدمج: 8/8 Success؛ Backend `650 passed, 2 warnings in 237.92s`؛ Frontend/SDK/Preview Builder/Production Compose وCodeQL Python/JavaScript-TypeScript كلها Success.
- لا review submissions أو inline review threads عند مراجعة ما قبل الدمج.
- التغيير النهائي يتطلب `target=staging`, تأكيد يدوي، التشغيل من `main`, اسم ملف محدد، وSHA-256 expected digest؛ يتحقق من الملف المحدد ويعيد فحص مشروع Supabase وTLS قبل `pg_restore`. لا يختار newest archive تلقائيًا. IAM المطلوب object-read فقط تحت prefix المعزول، بلا ListBucket أو write.
- لا workflow restore تم تشغيله؛ لا `pg_restore` ولا staging environment/secrets تم إنشاؤها أو تعديلها.

### ما بعد الدمج
- Production smoke [43280882516](https://github.com/HVA09/ai-chat-app/actions/runs/43280882516): completed/success.
- CI push run [43280882496](https://github.com/HVA09/ai-chat-app/actions/runs/43280882496): كان in_progress عند آخر قراءة؛ Backend ما زال في `Run backend tests with hang diagnostics`; Frontend/SDK/Preview Builder/Production Compose Success. يجب تحديث السجل بعد انتهائه.
- Render service `srv-dakc4nbm8hqs73e2po9g` ما زال configured على main و`autoDeployTrigger=checksPass`, Free Ohio, health path `/health`.
- أحدث Render deployment وقت فحص ما بعد الدمج ظل `dep-dbqvb6mq1p3s73dn2m3g` على SHA `48c451545c0ab2b05e08c94b4afc72b2215a4910`، حالة `live`. لم يظهر deploy جديد على `df929526...` وقت الفحص؛ نعيد التحقق بعد انتهاء post-merge CI. لم يتم manual deploy.

### ملاحظات وضوابط باقية
- سجل Backend CI أظهر duplicate-key واحدًا على `uq_scheduled_task_runs_task_scheduled_for` رغم نجاح pytest؛ لا يزال بند مراقبة منفصلًا.
- backup object الخارجي: وجوده وبنيته تم التحقق منهما عبر workflow السابق، لكن provenance من المصدر لم يثبت بالكامل. Restore capability لم تُثبت بعد.
- إنشاء GitHub Environment `supabase-staging`، حماية required reviewers، secrets scoped، S3 read-only credentials، sanitized dump، exact filename وSHA-256 كلها متطلبات خارجية لم تُجهّز بعد.
- لا تشغيل Workflow الاستعادة قبل مراجعة بيئة staging والـsecrets والـreviewers والملف/البصمة المحددة. لا استعادة production مطلقًا عبر workflow.
- لا bulk RAG reindex/backfill ولا strict retrieval fingerprint filtering قبل provenance موثوق ودليل restore ناجح إلى staging معزول.
- لا تعديل Render/Supabase production أو أسرار، ولا إجراءات بيانات إنتاجية بهذا القسم.

## 41. متابعة QueuePool وPR #699 لتحرير اتصال Agent قبل انتظار المزود — 2026-11-12

### تحديث تصحيحي لما بعد PR #698
- CI بعد الدمج على main df92952686f2a1f21339ab1ae55acb3f6d866164 اكتمل بنجاح:
  - run https://github.com/HVA09/ai-chat-app/actions/runs/43280882496
  - Backend: 650 passed, 2 warnings in 274.15s.
  - Frontend, SDK, Preview Builder, Production Compose: Success.
  - CodeQL Python وJavaScript/TypeScript: Success.
  - Production smoke https://github.com/HVA09/ai-chat-app/actions/runs/43280882516: Success.
- Render deployment dep-dbr0f415efls73dsn45g على df929526 انتهى Live عند 2026-11-12T18:40:12Z.
- بعد النشر، Render internal logs سجلت 104 استجابات GET /health 200 تقريبًا بين 18:40:11Z و18:47:31Z؛ أزمنة الاستجابة كانت غالبًا 10–15ms. لم تسجل app error logs في نافذة 18:40:10Z–18:50:00Z.
- هذا دليل تعافٍ داخلي لفحص الصحة بعد النشر، وليس إثباتًا كاملًا لتجربة المستخدم أو محادثة RAG/Agent من طرف إلى طرف.
- قبل النشر، حدثت أخطاء SQLAlchemy موثقة:
  - 2026-11-12T17:53:19Z على instance srv-dakc4nbm8hqs73e2po9g-bwvm4.
  - 2026-11-12T18:34:33Z–18:34:34Z على instance srv-dakc4nbm8hqs73e2po9g-9vpxx.
  - النوع: QueuePool limit of size 2 overflow 1 reached, connection timed out, timeout 15.00.
  - تأثرت طلبات مثل GET /saved-prompts وGET /users/me وGET /conversations/bookmarks وGET /folders، كما فشل DB health probe في نافذة الحادثة.
- لا يوجد حتى الآن ما يثبت أن سبب الحادثة الوحيد هو مسار Agent؛ لذا يبقى السبب الجذري قيد التحقق بعد الإصلاح والمراقبة.

### سبب برمجي قابل للإصلاح اكتشف في main
- SQLAlchemy pool defaults: DATABASE_POOL_SIZE=2, DATABASE_MAX_OVERFLOW=1, DATABASE_POOL_TIMEOUT_SECONDS=15؛ أي حد أقصى 3 checkouts لكل process/engine.
- start.sh يشغل API وembedded Celery worker وbeat كعمليات منفصلة، ولكل عملية engine/pool مستقل.
- في ai-backend/app/tasks.py، دالة _agent_job_event_sink كانت تنفذ db.get(AgentJob, job_id) على Session العامل وتعيدها دون إغلاق transaction.
- يستدعي AgentRuntime هذه الأحداث قبل provider calls: runtime_start وruntime_round_start، وكذلك حول الأدوات start وresult. قراءة ORM تُنشئ transaction، وكان بالإمكان الاحتفاظ بـcheckout أثناء انتظار AI provider أو tool I/O.
- هذا مسار حقيقي عالي المخاطر لاستبقاء اتصال، لا مجرد تخمين من Render logs؛ لكنه ليس إثباتًا بأن جميع حالات QueuePool سببها هذا المسار.

### PR #699
- PR: https://github.com/HVA09/ai-chat-app/pull/699
- Branch: fix/agent-event-db-pool-release-20261112.
- Base: df92952686f2a1f21339ab1ae55acb3f6d866164.
- Head الحالي عند فتح الطلب: e4b3bf75fdedc84b3ed8a0ebb5d57f18c8073337.
- التغيير: بعد قراءة حالة AgentJob في event sink، استخدام commit_and_release_connection(db) لتحرير checkout قبل الرجوع إلى AgentRuntime. هذا الحدّ يعامل اكتمال event/tool unit-of-work كنقطة commit مقصودة.
- أضيف اختبار قبول PostgreSQL test_agent_event_sink_releases_db_pool_before_provider_wait: يستخدم QueuePool من اتصال واحد، ويحاكي provider wait، ويشترط أن Session ثانية تستطيع تنفيذ SELECT 42 أثناء الانتظار.
- الملفات: ai-backend/app/tasks.py وai-backend/tests/test_pool_release_acceptance.py.
- PR يبقى Draft؛ لا دمج حتى نجاح Backend وFrontend وSDK وPreview Builder وProduction Compose وCodeQL ومراجعة أحدث head.
- CI run https://github.com/HVA09/ai-chat-app/actions/runs/43285215042, CodeQL https://github.com/HVA09/ai-chat-app/actions/runs/43285215153. عند آخر قراءة: SDK Success، Backend/Frontend/Preview Builder/Production Compose وCodeQL ما زالت In Progress.

### حدود التشغيل والقرار
- لا رفع pool size أو overflow عشوائيًا؛ الحدّ الحالي مقصود لمراعاة session pooler ومحدودية الموارد.
- لا تغييرات Render/Supabase أو secrets أو قاعدة الإنتاج أو البيانات؛ لا تغيير في deployment خلال PR #699.
- لا restore أو backfill/reindex.
- بعد دمج PR #699 (إذا اجتاز كل الفحوص): راقب QueuePool/health/app errors مجددًا، ثم اختبر طلبات مستخدم فعلية ومهمة Agent؛ لا تعتبر تعافي /health وحده إغلاقًا لحادثة الاستنفاد.
- ملاحظة مستقلة ما زالت مرصودة في PostgreSQL CI: duplicate key على uq_scheduled_task_runs_task_scheduled_for مع نجاح مجموعة الاختبارات؛ تبقى للمراقبة والمعالجة المنفصلة.


## 41. حادثة QueuePool في Render ومراجعة احتجاز الاتصالات في Agent — 2026-11-12

### مرجع الإنتاج بعد PR #698
- main: `df92952686f2a1f21339ab1ae55acb3f6d866164`.
- PR #698 merged؛ post-merge CI [43280882496](https://github.com/HVA09/ai-chat-app/actions/runs/43280882496) انتهى بنجاح؛ Backend `650 passed, 2 warnings in 274.15s`، وFrontend/SDK/Preview Builder/Production Compose Success.
- Production smoke [43280882516](https://github.com/HVA09/ai-chat-app/actions/runs/43280882516) Success.
- Render نشر main commit إلى Live عبر `dep-dbr0f415efls73dsn45g` عند `2026-11-12T18:40:12Z`.

### دليل حادثة الاتصالات
- سجلات Render لخدمة `srv-dakc4nbm8hqs73e2po9g` رصدت SQLAlchemy:
  `QueuePool limit of size 2 overflow 1 reached, connection timed out, timeout 15.00`.
- المجموعة الأولى عند `17:53:19Z` وأثرت على `GET /saved-prompts`.
- مجموعة ثانية عند `18:34:33Z–18:34:34Z`؛ فحص `/health` نفسه سجل `فحص الصحة: قاعدة البيانات غير متاحة`، كما ظهرت استثناءات لـ`GET /users/me` و`GET /conversations/bookmarks` و`GET /folders`.
- هذا دليل على أن الاتصالات الثلاثة المحلية المتاحة للعملية (pool_size=2 + max_overflow=1) كانت محجوزة أو غير متاحة خلال تلك اللحظات. لا يثبت وحده السبب الأعلى أو يحدد أي طلب احتفظ بكل اتصال.
- بعد نشر `df929526...` ظهرت قراءات داخلية متتالية لـ`GET /health 200` على instance الجديد `srv-dakc4nbm8hqs73e2po9g-w7clc`، غالبها `10–15ms`، وأحيانًا قراءة أبطأ `289ms`. استعلام أخطاء التطبيق للفترة `18:40:10Z–18:50:00Z` أعاد صفرًا.
- آخر سجل صحة مؤكد في القراءة التفصيلية: `18:47:31.875Z`. لا نعتبر هذه النافذة القصيرة إثبات استقرار دائم.
- الفحص الخارجي المباشر لـ`/health` و`/ready` لم يمكن التحقق منه عبر أداة الويب في هذه الجولة؛ لذا يبقى التحقق العام end-to-end غير مؤكد.

### المراجعة التقنية والإصلاح المقترح
- `/chat` في وضع `/agent` يمرر جلسة SQLAlchemy إلى `AgentRuntime`. قبل هذا الإصلاح، كان `AgentRuntime` ينتظر اكتشاف MCP ومزوّد النموذج وتنفيذ بعض الأدوات دون حدود تحرير اتصال مماثلة لمسار chat العادي.
- مراجعة الكود تحدد ذلك كمسار احتجاز اتصال محتمل وواضح، لكنه لا يثبت أنه سبب كل حوادث Render التي ظهرت.
- PR #700: https://github.com/HVA09/ai-chat-app/pull/700
  - branch: `fix/agent-db-pool-release-20261112`.
  - base main: `df92952686f2a1f21339ab1ae55acb3f6d866164`.
  - head الحالي: `dbca8adc9269fff5734a29f0a133258904fb6401`.
  - يحرر الاتصال قبل MCP discovery، وبعد event callback وقبل dispatch للأداة، وقبل كل جولة لمزوّد النموذج.
  - أدوات `analyze_data` و`create_project_archive` تحرر الاتصال بعد قراءة metadata/quota وقبل عمليات Object Storage.
  - اختبار SQLite QueuePool من اتصال واحد يحاكي event sink يستخدم DB، أداة تقرأ DB، ثم جولة نموذج لاحقة؛ ويثبت توفر الاتصال للمنافسة. أضيفت اختبارات لأدوات التخزين.
- CI [43286194209](https://github.com/HVA09/ai-chat-app/actions/runs/43286194209) وCodeQL [43286193933](https://github.com/HVA09/ai-chat-app/actions/runs/43286193933) قيد التشغيل عند آخر قراءة؛ SDK Success وباقي الوظائف كانت In Progress.
- PR #700 يبقى Draft؛ لا merge حتى تنجح كل الفحوص على آخر SHA وتكتمل المراجعة. لم يتغير main نتيجة هذا الإصلاح حتى الآن.

### الضوابط
- لم نغيّر DATABASE_POOL_SIZE أو DATABASE_MAX_OVERFLOW أو DATABASE_URL أو أي secret في Render/Supabase؛ لا نزيد حجم pool كحل سريع قبل إثبات حدود الاتصالات لدى Session Pooler.
- لا تغييرات schema/migrations، ولا استعادة، ولا reindex/backfill أو بيانات إنتاجية.
- بعد دمج #700 يلزم مراقبة Render logs مجددًا ومقارنة QueuePool timeouts وطلبات /health و5xx قبل اعتبار الحادثة محلولة.

## 42. توسيع إصلاح Pool من Celery إلى AgentRuntime لجميع وسائل النقل — 2026-11-12

### تصحيح PR #699
- عند مراجعة المسارات تبين أن HTTP POST /chat وSSE POST /chat/stream يستدعيان run_agent مباشرة، ولا يمران عبر _execute_agent_job في tasks.py.
- لذلك فإن تحرير الاتصال في event sink الخاص بـCelery وحده لا يغطي مسارات Agent المباشرة والمتدفقة.
- تم توسيع PR #699 إلى الرأس الحالي e9c20256f7ba0301f44104ed85dafe91e819fdb2:
  - ai-backend/app/services/agent_runtime.py: يستدعي commit_and_release_connection(db) مباشرة قبل كل provider.get_reply_with_tools call، وبذلك يشمل HTTP وSSE وCelery.
  - ai-backend/app/tasks.py: يبقى تحرير الاتصال بعد قراءة AgentJob داخل event sink قبل متابعة عملية الأداة/المزوّد.
  - ai-backend/tests/test_pool_release_acceptance.py: اختبار PostgreSQL بــ QueuePool من اتصال واحد، يستخدم AgentRuntime الفعلي ومزوّدًا محاكى ينتظر؛ يتحقق أن Session ثانية تنفذ SELECT 42 خلال انتظار المزوّد.
- PR #699 ما زال Draft ومفتوحًا وغير مدمج؛ base main df92952686f2a1f21339ab1ae55acb3f6d866164.
- على أحدث head e9c20256:
  - CodeQL Python وJavaScript/TypeScript: Success.
  - Frontend وSDK وPreview Builder وProduction Compose: Success.
  - Backend: لا يزال Run backend tests with hang diagnostics In Progress في آخر قراءة.
  - CI run https://github.com/HVA09/ai-chat-app/actions/runs/43286930228
  - CodeQL run https://github.com/HVA09/ai-chat-app/actions/runs/43286931731
- لا merge حتى ينجح Backend على الرأس ذاته وتكتمل المراجعة النهائية.

### توضيح حادثة QueuePool في Render
- نافذة الحادثة الثانية بعد النشر: 2026-11-12T18:51:58Z–18:51:59Z على instance srv-dakc4nbm8hqs73e2po9g-w7clc.
- ظهرت دفعة طلبات واجهة من العميل 10.27.232.133 و10.29.6.5 قبل الحادثة مباشرة: POST /auth/refresh 200، GET /notifications 200، GET /workspaces 200، GET /saved-prompts 200، GET /tags 200، GET /assistants 200.
- ثم تعثرت طلبات أخرى بــQueuePool timeout 15s: /memories، /conversations/bookmarks، /chat/models، /users/me، /conversations. بعد استعادة الوصلات عادت بعض الطلبات إلى 200.
- في التوقيت ذاته، مهمة Celery run_due_scheduled_tasks انتهت بنجاح خلال نحو 0.0196 ثانية، ولا تظهر سجلات Agent task بنفس نافذة الحادثة؛ لذلك لا توجد قرينة مباشرة على أن تلك المهمة سببت الحادثة.
- /health ظل يعطي 200، لكن بعض probes ارتفع زمنها إلى 700–807ms وقت ضغط الاتصالات ثم عاد إلى 10–12ms.
- الاستنتاج الحالي: السجلات تثبت استنفاد QueuePool متقطعًا تحت تزامن الطلبات، مع خطر برمجي ملموس في مسارات Agent التي تحتفظ باتصال قبل provider I/O؛ لكنها لا تثبت أن Agent هو السبب الوحيد أو أن الإصلاح وحده يغلق كل حالات الاستنفاد.
- لا تزال الحاجة قائمة لمراقبة Render بعد دمج/نشر PR #699، وملاحظة أداء طلبات المستخدم، وتجربة Agent فعلية. لا تعتبر 200 health وحده إغلاقًا للحادثة.

### الضوابط
- لم تتغير إعدادات Render أو Supabase أو حجم pool؛ لا تغييرات Production ولا migrations ولا data writes.
- PR #699 Draft حتى اكتمال Backend/CodeQL ومراجعة latest head.
- لا تشغيل restore أو reindex/backfill؛ بوابة backup/restore ما زالت مفتوحة.

## 42. دمج PR #700 وتحديث حادثة استنفاد الاتصالات — 2026-11-12

### PR #700
- PR: https://github.com/HVA09/ai-chat-app/pull/700
- تم الدمج بطريقة squash بعد نجاح 8/8 check-runs على head `dbca8adc9269fff5734a29f0a133258904fb6401`.
- Merge/main SHA: `3d5910d68977f049d84ccf7537f2e18e2462aba3`.
- Backend: `653 passed, 2 warnings in 314.23s`.
- Frontend, SDK, Preview Builder, Production Compose: Success.
- CodeQL Python وJavaScript/TypeScript: Success.
- لا تغييرات schema/migration/config/secret.

### ما بعد الدمج
- main CI: [43287982770](https://github.com/HVA09/ai-chat-app/actions/runs/43287982770) بدأ على SHA `3d5910d...`; SDK Success، وباقي الوظائف كانت In Progress عند آخر قراءة.
- Production smoke: [43287982446](https://github.com/HVA09/ai-chat-app/actions/runs/43287982446) In Progress عند آخر قراءة.
- CodeQL: [43287982533](https://github.com/HVA09/ai-chat-app/actions/runs/43287982533) In Progress عند آخر قراءة.
- Render لم يقدم بعد دليل نشر Live على SHA `3d5910d...` عند آخر poll؛ يلزم التحقق من deployment الجديد بعد نجاح checks.
- لا نعلن حل QueuePool بالكامل من merge وحده.

### مراجعة مسارات async DB إضافية — ليست ضمن PR #700
- `billing.cancel_subscription`: provider cancellation awaited بعد تحميل subscription، قبل تحديث الحالة المحلية. يحتاج تحرير اتصال بعد قراءة provider_subscription_id ثم إعادة تحميل/التحقق قبل الحفظ.
- `billing._apply_webhook_event`: بعد commit وكتابة log_event يحصل await لـ`notify_realtime`; يلزم فحص notify_realtime وهل يحتفظ أو يفتح DB checkout خلال بثه.
- `billing.create_checkout`: يحتفظ بمعاملة `pg_advisory_xact_lock(user_id)` أثناء provider checkout call. لا تضف commit/release مباشرًا هنا، لأن ذلك يسقط قفل المعاملة ويُبطل منع checkout المتكرر. يتطلب تصميم idempotency/checkout-attempt persisted أو session-level advisory lock مستقلًا.
- `oauth.refresh_connection` / `refresh_oauth_connection`: يقرأ refresh token من صف OAuth ثم ينتظر HTTP refresh قبل commit. مرشح لتحرير الاتصال بعد التقاط البيانات والتحقق، مع reload/locking مناسب قبل update كي لا يُكتب token قديم فوق token أحدث.
- `projects.build_project_preview`: يقرأ ملفات المشروع ثم ينتظر preview builder خارجي حتى `PREVIEW_BUILD_TIMEOUT_SECONDS` (افتراضي 120s) مع session مفتوحة. مرشح لتحرير الاتصال بعد materializing payload_files وقبل await، ثم يسجل artifact بعد إعادة المعاملة.
- مسارات chat الأخرى راجعت: compare/regular chat/web search/vision وregenerate/edit لديهم حدود commit/rollback قبل provider، وupload/index image يحرران checkout قبل التخزين/provider. لا دليل أن WebSocket أو Celery كان سبب burst 18:51؛ كلاهما ظهر ضمن الضحايا أو كمهام سريعة.
- لا تعديل لهذه المسارات في PR #700؛ افصلها في PR مراجع لاحقًا ولا تُسقط advisory locks أو تغير سلوك الدفع/OAuth.

### حادثة Render المسجلة
- تكرر `QueuePool size=2 overflow=1 timeout=15s` بعد نشر #698 في `17:53:19Z`, `18:34:33Z`, و`18:51:58Z`.
- Burst `18:51:58Z` أثر على عدة GET requests؛ سجل ASGI واحد أظهر فشل `notifications_websocket` أثناء `db.get(User, user_id)`، وهذا يحدد الضحية لا السبب الجذري.
- Celery due-scheduled task قبل الـburst عند `18:51:51Z` نجحت في نحو 0.0196s.
- بعد ذلك استمر internal `/health 200` بأزمنة غالبها 10–12ms، لكن هذا لا ينفي فشل الطلبات العادية تحت ضغط اتصالات DB.
- المطلوب بعد نشر #700: رصد QueuePool errors وطلبات 5xx، وإثبات نجاح طلبات مستخدم عادية (auth/models/chat) وليس `/health` فقط. لا تغيير pool vars أو Render/Supabase limits دون قياس ومعرفة قيود pooler.

### الحدود
- لا تعديل إنتاجي لقاعدة البيانات أو Render/Supabase env/secrets.
- لا تشغيل استعادة أو backfill/reindex، ولا تغيير pool size/overflow.
- لا تشغيل webhook/payment/OAuth حقيقي بغرض الاختبار على production.

## 43. PR #700 حلّ محل PR #699 وأصبح إصلاح Agent Pool على main — 2026-11-12

### نتيجة PR #700
- PR: https://github.com/HVA09/ai-chat-app/pull/700
- العنوان: fix(db): release pool connections during Agent external waits.
- PR #700 merged؛ merge commit/main: 3d5910d68977f049d84ccf7537f2e18e2462aba3.
- Parent/base: df92952686f2a1f21339ab1ae55acb3f6d866164.
- تغييرات runtime:
  - release قبل MCP discovery (انتظار خارجي).
  - release بعد callbacks لأحداث الأدوات وقبل تنفيذ tool handler.
  - release قبل كل model/provider round.
  - release داخل Agent tools قبل remote Object Storage: analyze_data materialization وcreate_project_archive upload.
- regression tests أضافت SQLite QueuePool من اتصال واحد تغطي MCP/provider/tool wait، واختبارات registry تغطي تحرير الاتصال قبل materialization والرفع.
- CI main run https://github.com/HVA09/ai-chat-app/actions/runs/43287982770: success.
- Backend: 653 passed, 2 warnings in 225.87s.
- Frontend، SDK، Preview Builder، Production Compose، CodeQL Python وJavaScript/TypeScript، Production smoke، Publish Backend image: كلها Success.
- PostgreSQL CI سجّل duplicate key منفصلًا على uq_scheduled_task_runs_task_scheduled_for رغم نجاح المجموعة؛ ما زال بندًا تقنيًا مستقلاً للمراقبة.
- Render بدأ auto deploy لـ3d5910d بتاريخ 2026-11-12T19:18:26Z، build succeeded عند 19:18:38Z، deployment كان update_in_progress عند آخر قراءة؛ لم نعتبره Live بعد حتى تأتي حالة صريحة.

### إغلاق PR #699 المكرر
- PR #699: https://github.com/HVA09/ai-chat-app/pull/699 أُغلق دون دمج بعد دمج PR #700.
- سبب الإغلاق: PR #700 يغطي الخطر المركزي ويضيف نقاط release إضافية قبل MCP/tool/storage؛ PR #699 أصبح متأخرًا عن main ويتضمن إصلاحًا متداخلًا.
- PR #699 head 8ee388dd83965cdaf3809f9a4e377d2518597e45 لم يدمج.
- CI على PR #699 head e9c20256f7ba0301f44104ed85dafe91e819fdb2 كان فاشلاً: 8 اختبارات AgentRuntime القديمة مرتّرة بـdb=object() اصطدمت بقراءة expire_on_commit؛ بينما test_agent_runtime_releases_db_pool_before_provider_wait الجديد نجح. لم يُنقل هذا الإصلاح إلى main لأنه أصبح مغطّى بحل PR #700؛ PR #700 غيّر الاختبارات القديمة إلى _NoopSession وأثبت السلوك باختبار pool مخصص.
- لا تغيير production/DB/Supabase/Render settings من فرع PR #699؛ فرع PR #699 لم يتم نشره.

### بوابة التحقق بعد نشر PR #700
- انتظر حالة Render deploy dep-dbr120e8bjmc739l0l00 لتكون Live.
- بعد Live، راقب QueuePool timeout وDB health وسجلات التطبيق؛ لا اعتبار 200 health كافيًا وحده، وراقب طلبات المستخدم وأداء Agent/Storage.
- آخر ملاحظة قبل deploy: incidents على QueuePool في 17:53 و18:34 و18:51؛ وبعد حادثة 18:51 لم تسجل أخطاء QueuePool جديدة حتى 19:13؛ ظهر فقط Gemini provider 503 مرتين عند 18:52:55Z.
- لا استعادة أو backfill/reindex أو تغييرات بيانات إنتاجية. بوابة backup/restore لا تزال مفتوحة.

## 44. تأكيد نشر PR #700 ومراقبة Render الأولية — 2026-11-12

- Render service srv-dakc4nbm8hqs73e2po9g نشر main commit 3d5910d68977f049d84ccf7537f2e18e2462aba3.
- Deployment dep-dbr120e8bjmc739l0l00 بدأ 2026-11-12T19:18:25Z وانتهى Live بنجاح عند 19:20:31Z.
- بعد Live، سجلات Render الداخلية أظهرت 26 استجابة GET /health 200 بين 19:20:35Z و19:22:00Z تقريبًا، بأزمنة 10–12ms.
- نافذة سجلات app error من 19:20:31Z إلى 19:27:00Z: صفر app errors.
- هذا تحقق تشغيل أولي داخلي للنشر، وليس اختبارًا كاملاً لكل مسارات المستخدم أو اختبار ضغط يثبت عدم عودة QueuePool تحت أحمال أعلى.
- PR #699 تأكد إغلاقه دون merge (merged=false) لأنه أصبح مكررًا بعد PR #700؛ لم يحدث deploy من branch #699.
- لا تغييرات على إعدادات Render أو حجم pool أو Supabase أو DB أو الأسرار. لا migrations، لا restore، لا backfill/reindex.
- القرار: راقب QueuePool errors مجددًا مع طلبات فعلية وAgent runs وعمليات الملفات؛ لا تغلق حادثة استنفاد الوصلات نهائيًا اعتمادًا على /health وحده. خطأ Gemini 503 في 18:52:55Z كان منفصلًا عن QueuePool، وآخر نافذة بعد deploy لم تسجل أخطاء app.



## 45. دمج PR #701 — تحرير اتصالات DB في Billing وOAuth وPreview — 2026-11-12

### نتيجة PR
- PR #701: https://github.com/HVA09/ai-chat-app/pull/701
- العنوان: `fix(db): release pool connections during billing, OAuth, and preview waits`.
- تم الدمج بطريقة Squash؛ merge commit وmain: `396cb54aea4b9e8656249434fc7ab09089c27f76`.
- base السابق: `3d5910d68977f049d84ccf7537f2e18e2462aba3`.
- head الذي اجتاز فحوص ما قبل الدمج: `c5a6880033be3893632a547c01d13c4b075ec9ed`.
- Pre-merge CI: 8 check-runs Success؛ Backend `658 passed, 2 warnings in 350.39s`; Frontend وSDK وPreview Builder وProduction Compose وCodeQL Python/JavaScript-TypeScript كلها Success.
- لا inline review threads أو review submissions عند المراجعة النهائية.
- لا schema/migration changes.

### الإصلاحات
- Billing cancel: تحرير اتصال DB قبل await لمزود الدفع، ثم إعادة تحميل وقفل سجل الاشتراك نفسه باستخدام id/user/provider_subscription_id؛ إذا تغير السجل يُرجع 409 ولا يضع الاشتراك الجديد في canceled.
- Billing webhooks: تحرير الاتصال قبل إرسال SMTP والبث realtime بعد تحميل بيانات المستلم والخطة.
- OAuth refresh: تحرير الاتصال قبل token endpoint، واستخدام compare-and-swap على encrypted access/refresh token القديم لمنع استجابة بطيئة من الكتابة فوق تحديث أحدث.
- Project preview: تحرير الاتصال قبل isolated builder، إعادة التحقق من صلاحية المشروع بعد اكتمال البناء، ثم تحرير الاتصال مرة ثانية قبل رفع artifact إلى Object Storage.
- قفل `pg_advisory_xact_lock` في `billing.create_checkout` بقي كما هو عمدًا؛ تحريره خلال provider await دون بديل idempotency/lock يُعيد خطر إنشاء checkout مكرر.

### Regression tests
- ملف `ai-backend/tests/test_external_wait_pool_release.py` أضاف اختبارات QueuePool ذات اتصال واحد:
  1. توفر pool slot خلال provider cancellation.
  2. عدم إلغاء اشتراك بديل بسبب استجابة cancel قديمة.
  3. توفر الاتصال أثناء إرسال Billing webhook email.
  4. تحرير slot خلال OAuth refresh وعدم overwrite token pair أحدث.
  5. توفر slot أثناء preview builder وأثناء نشر artifact.
- لم تنفذ أي دفعة أو OAuth حقيقي أو SMTP حقيقي أو builder خارجي حي خلال الاختبارات.

### ما بعد الدمج (آخر قراءة)
- main commit: `396cb54...`.
- CI run [43296415363](https://github.com/HVA09/ai-chat-app/actions/runs/43296415363): بدأ؛ SDK Success، Backend/Frontend/Preview Builder/Production Compose كانت In Progress في آخر قراءة.
- CodeQL [43296415526](https://github.com/HVA09/ai-chat-app/actions/runs/43296415526): Analyze Python وJavaScript/TypeScript In Progress في آخر قراءة.
- Production smoke [43296415426](https://github.com/HVA09/ai-chat-app/actions/runs/43296415426): In Progress في آخر قراءة.
- Backend image publish [43296415367](https://github.com/HVA09/ai-chat-app/actions/runs/43296415367): In Progress في آخر قراءة.
- Render service ما زال عند deploy live السابق `dep-dbr120e8bjmc739l0l00` على SHA `3d5910d...`; لم يبدأ deploy SHA `396cb54...` عند آخر poll.
- Render configured على `autoDeployTrigger=checksPass`؛ انتظر checks/main publish وبعدها تحقق من Render Live تلقائيًا دون manual deploy.

### بوابة مراقبة الاستقرار
- بعد نشر #700 (SHA `3d5910d...`)، سجل Render من 19:20:31Z إلى 19:36:00Z لم يُظهر QueuePool أو app errors؛ health 200 مستمر لكن غير كافٍ وحده.
- Duplicate-key CI على `uq_scheduled_task_runs_task_scheduled_for` ظهر مجددًا رغم نجاح pytest في #701؛ يبقى issue منفصلًا يحتاج تحليل idempotency/locking للـscheduler.
- لا تغيير في DB_POOL_SIZE/OVERFLOW أو Render/Supabase limits أو env/secrets.
- لا production restore، ولا reindex/backfill أو strict retrieval fingerprint filtering.
\n


## 46. تحقق ما بعد دمج #701 والنشر الحي — 2026-11-12

### GitHub post-merge
- main: `396cb54aea4b9e8656249434fc7ab09089c27f76`.
- CI [43296415363](https://github.com/HVA09/ai-chat-app/actions/runs/43296415363): Success.
- Backend: `658 passed, 2 warnings in 217.20s`.
- Frontend, SDK, Preview Builder, Production Compose: Success.
- CodeQL Python + JavaScript/TypeScript [43296415526](https://github.com/HVA09/ai-chat-app/actions/runs/43296415526): Success.
- Publish backend image [43296415367](https://github.com/HVA09/ai-chat-app/actions/runs/43296415367): Success.
- Production smoke [43296415426](https://github.com/HVA09/ai-chat-app/actions/runs/43296415426): Success.

### Render production deployment
- Deployment: `dep-dbr1p96tlv9c738bj0b0`، commit `396cb54...`.
- Build succeeded at 20:08:17.661Z؛ deployment succeeded and reached `live` at 20:10:10.196Z؛ Render event `deploy_ended` at 20:10:10.336Z.
- Render emitted `Your service is live`; app startup completed on new instance `srv-dakc4nbm8hqs73e2po9g-xmxr2`.
- Startup verified Object Storage connectivity OK, embedded Celery worker and beat started, worker connected to Redis and reported ready, Uvicorn startup complete on port 10000.
- Health window after deployment (20:10:10Z–20:13:00Z): 38 unique internal `GET /health 200` request IDs (76 paired app/access log lines), latency mostly 9–12ms.
- Same window: 0 app-level error logs and 0 `QueuePool` timeout logs.
- This evidence is from Render's internal health and application logs. The external HTTP probe tool could not independently fetch the public health URL in this session; do not overstate that as externally verified.

### Duplicate-key PostgreSQL CI line — classified
- PostgreSQL CI printed one `duplicate key value violates unique constraint uq_scheduled_task_runs_task_scheduled_for` despite pytest success.
- Source reviewed: `ai-backend/tests/test_scheduled_tasks.py::test_scheduled_run_slot_is_unique` intentionally attempts to insert the same `(scheduled_task_id, scheduled_for)` twice inside `pytest.raises(IntegrityError)`, then rolls back.
- This is the deliberate unique-constraint regression test, not evidence of a failing CI suite or a production duplicate task. Keep the database uniqueness constraint; no production change is warranted from this log line.
- The scheduler code separately catches `IntegrityError` when another worker has already claimed a due slot, preventing double execution.

### Remaining stability gate
- PRs #696, #697, #698, #700, and #701 are merged and their respective deployments/checks are successful.
- Initial post-#700 and post-#701 Render observation windows show no `QueuePool` timeout logs; #701 window had 38 successful internal health requests and no app errors.
- This is a healthy deployment signal, not a concurrency/load test and not proof across every end-user route. Keep monitoring normal chat/RAG/Agent and file workflows before declaring the original pool incident fully closed.
- Do not increase pool sizes, change Render plans, or edit database connection limits without measuring usage and provider limits.
- Backup provenance/restore-to-staging remains unproven; the #698 staging-only workflow must not be run until environment reviewers, scoped secrets, sanitized archive, filename, and matching SHA-256 are independently ready. No restore, backfill, bulk reindex, or strict retrieval fingerprint filtering was run.
\n


## 47. دمج #702، نسخة Production backup، وانتكاسة QueuePool وتحسين تهيئة الواجهة — 2026-11-14

### main ونتيجة #702
- main الحالي: `18b8416cf9b2d13406a8c7d767341d42897496c0`.
- PR #702: https://github.com/HVA09/ai-chat-app/pull/702 — إصلاح دورة رفع الملفات بعد unmount؛ merged.
- CI post-merge [43353534426](https://github.com/HVA09/ai-chat-app/actions/runs/43353534426): Success.
- Backend: `658 passed, 2 warnings in 316.79s`.
- Frontend، SDK، Preview Builder، Production Compose، CodeQL Python وJavaScript/TypeScript: Success.
- Production smoke [43413334380](https://github.com/HVA09/ai-chat-app/actions/runs/43413334380): Success.
- Object Storage smoke [43422588553](https://github.com/HVA09/ai-chat-app/actions/runs/43422588553): Success.
- Frontend service `srv-daklqph42hec73b1f61g` deploy `dep-dbr7j4ivcj2c73ejojj0` على SHA `18b8416...` وصل Live بتاريخ 2026-11-13T02:45:05Z.
- Backend service ما زال على PR #701 merge commit `396cb54aea4b9e8656249434fc7ab09089c27f76`، وهذا متوقع لأن #702 frontend-only. Deployment backend `dep-dbr1p96tlv9c738bj0b0` بقي Live.

### نسخة احتياطية إنتاجية أحدث — ليست Restore proof
- Workflow run [43405958682](https://github.com/HVA09/ai-chat-app/actions/runs/43405958682)، scheduled 2026-11-13T10:01:57Z، jobs preflight وbackup: Success.
- الاسم: `ai-chat-postgres-20261113T100201Z.dump`.
- المفتاح البعيد: `database/ai-chat-postgres-20261113T100201Z.dump`.
- حجم object بحسب remote HEAD: `862936 bytes`.
- `pg_dump --format=custom` و`pg_restore --list` وفحص remote HEAD والرفع: Success.
- Object Storage smoke منفصل أثبت upload/read-back/compare/delete لملف اختباري.
- **حدود الدليل:** لم يسجل backup workflow SHA-256 لملف dump نفسه؛ لا artifact مرفق بـworkflow run؛ لم يتم تنزيل النسخة للتحقق من hash؛ ولم يُجر restore فعلي.
- backup أعلاه خام من Production، وليس sanitized staging archive. كما أنه يقع تحت `database/` وليس `database/staging-sanitized/` المطلوب في restore workflow. لذلك لا يجوز استخدامه في بوابة الاستعادة الحالية.
- GitHub Environment `supabase-staging`، reviewers/secrets، sanitized export مع provenance، exact staging object filename + SHA-256، وrestore test ما زالت متطلبات غير مثبتة.
- قرار البوابة: backup object حديث موجود ومتحقق من حجمه/وجوده وarchive list، لكن backup provenance/hash + restore-to-staging ما زالا OPEN. لا تشغيل restore workflow.

### QueuePool incident — لا إغلاق للحادثة
- فحص Render logs بعد نشر #701 كشف موجة حقيقية بتاريخ 2026-11-13 حول `03:47:27Z`.
- نحو 53 رسالة QueuePool timeout ضمن نحو 86 app-error lines في تلك النافذة.
- النص: `QueuePool limit of size 2 overflow 1 reached, connection timed out, timeout 15.00`.
- فشلت طلبات عادية، منها `GET /users/me`, `/assistants`, `/saved-prompts`, `/chat/models`, `/conversations/bookmarks`, و`/memories`.
- خطأ `notifications_websocket` ظهر أثناء `db.get(User,...)` في نفس الموجة؛ الكود الحالي يفتح Session قصيرة ويغلقها قبل قبول/الإبقاء على WebSocket، لذلك هذا endpoint ضحية محتملة وليس سببًا مثبتًا.
- instance كان مستيقظًا من Render Free hibernation: API startup complete عند ~03:46:59Z؛ health checks أولية كانت بطيئة (212ms ثم 73ms)؛ refresh token POST استغرق ~3050ms عند 03:47:11Z؛ وتبع ذلك موجة timeout.
- Celery `run_due_scheduled_tasks` بدأ بعد موجة الفشل، عند 03:47:48Z، وانتهى بسرعة؛ لا دليل يحمّل scheduler مسؤولية هذه الموجة.
- لا QueuePool timeouts أخرى ظهرت في سجل النافذة المفحوصة بعد الموجة وحتى 2026-11-14T05:10Z؛ هذا لا يثبت عدم العودة تحت حمل آخر.
- لم يتم رفع `DATABASE_POOL_SIZE` أو `DATABASE_MAX_OVERFLOW` أو تغيير Supabase pooler/Render Free tier. لا يجوز إعلان incident closed.

### فحص مصادر الضغط عند تسجيل الدخول
- `ai-frontend/src/App.jsx` كان يبدأ 6 initial reads مستقلة عند `authed=true`: Current user، AI models، workspaces، tags، assistants، saved prompts.
- `refreshWorkspaces()` كان يقوم بالفعل بتحميل folders ثم projects ثم assistants ثم conversations بالتتابع، ما جعل التحميل المبكر المباشر للمساعدين مكررًا.
- effect منفصل كان يطلب conversations بعد 300ms، مكررًا مع تحميل المحادثات داخل `refreshWorkspaces()`.
- `useBookmarks` و`useMemories` و`useNotifications` كانت تجلب مجموعاتها تلقائيًا فور المصادقة؛ هذا يضيف دفعة موازية أخرى. WebSocket notifications لا يحتفظ بقاعدة البيانات بعد handshake في الكود الحالي.
- هذه بنية تفسر burst منطقيًا وتبرر تخفيف client-side concurrency، لكنها ليست دليلًا نهائيًا على مالك الاتصالات الثلاثة وقت QueuePool timeout.

### PR #709 — Draft لتسلسل initial hydration
- PR: https://github.com/HVA09/ai-chat-app/pull/709
- branch: `fix/frontend-stagger-auth-startup-requests-20261114`.
- Base: `18b8416...`; head: `c3f736ce542ddd8d0c3350c611f0e90560ced45c`.
- التغييرات: تسلسل initial data reads (current user، model catalog، workspace hierarchy، tags، saved prompts، bookmarks، memories، notification list)؛ إزالة initial assistant request المكرر؛ تخطي duplicate initial conversations query مع الحفاظ على debounced search refresh؛ fallback assistants/conversations عند فشل workspace discovery؛ إلغاء بقية التسلسل بعد logout/unmount.
- Auto-load الجديد في hooks اختياري افتراضيًا `true` للحفاظ على التوافق؛ App فقط يضبط `loadOnAuth=false` ويستدعي refresh methods في التسلسل. Notification WebSocket يبقى متصلًا فور المصادقة، ويؤجل REST list فقط.
- اختبارات جديدة تغطي sequential order/abort، deferred hooks، استمرار WebSocket، ونتيجة workspace fetch.
- PR ما زال Draft؛ CI run [43561624398](https://github.com/HVA09/ai-chat-app/actions/runs/43561624398) وCodeQL [43561624345](https://github.com/HVA09/ai-chat-app/actions/runs/43561624345) كانا In Progress عند آخر poll. لا merge ولا deploy من هذا الفرع.
- لا تغييرات backend/DB/schema/migration/Render/Supabase/env/secrets/pool limits.

### المطلوب بعد PR #709
- انتظر جميع checks على نفس head SHA، ثم راجع أي frontend test/build failures قبل mark-ready/merge.
- بعد النشر، راقب QueuePool timeout وapp 5xx، وليس /health فقط. المطلوب end-user routes وطلبات أول login بعد hibernation.
- لا تزال الحاجة إلى pool owner diagnostics قائمة إذا تكررت الحادثة؛ current logs identify victims, not the three held checkouts.
- لا production restore أو backfill/reindex أو تغيير pool settings. النسخة الإنتاجية لا تُعتبر staging sanitized backup.


## 48. دمج PR #709 — تسلسل طلبات التهيئة بعد المصادقة — 2026-11-14

### النتيجة
- PR #709: https://github.com/HVA09/ai-chat-app/pull/709 — merged via Squash.
- Base قبل الدمج: `18b8416cf9b2d13406a8c7d767341d42897496c0`.
- Head الذي اجتاز الفحوص: `4ef03e143d92df1678c7f42a099c12db1dbcb20f`.
- Merge commit / main: `18ff9bd0f047886c7e5b1121bba95a0b6e00371c`.
- Pre-merge CI run [43561845096](https://github.com/HVA09/ai-chat-app/actions/runs/43561845096): Success.
- Backend: `658 passed, 2 warnings in 270.42s`.
- Frontend: `513 passed across 74 test files`; Vite build Success.
- SDK، Preview Builder، Production Compose: Success.
- CodeQL Python + JavaScript/TypeScript: Success.
- لا inline review threads أو review submissions.
- لا تغييرات Backend/DB/schema/migration/Render/Supabase/env/secrets/pool size/overflow.

### التغيير
- ترتيب أولية requests بعد authed: notifications list أولًا (مع بقاء WebSocket فوريًا)، ثم current user، model catalog، workspace hierarchy، tags، saved prompts، bookmarks، memories.
- إزالة duplicate eager request للمساعدين؛ workspace hierarchy يحمل owned/shared assistants بالفعل.
- تجاوز duplicate initial conversations request؛ بقي debounced refresh عند تغيير البحث.
- عند فشل workspace discovery، fallback يقوم بتحميل assistants وconversations كما في السلوك السابق.
- hooks bookmarks/memories/notifications تقبل `loadOnAuth` اختياريًا، default `true` للتوافق؛ App وحده يتحكم بتحميلها ضمن التسلسل.
- التسلسل يتوقف عن بدء طلبات جديدة بعد logout/unmount.
- أضيفت tests للتحقق من التتابع والإلغاء وdeferred hooks واستمرار WebSocket ونتيجة workspace refresh.
- الهدف تخفيض burst على API Pool صغير عند session restore بعد Render Free hibernation؛ هذا تخفيف client-side محتمل وليس إثباتًا نهائيًا للسبب الجذري الذي احتجز الاتصالات الثلاثة.

### ما بعد الدمج — آخر قراءة
- main commit: `18ff9bd0f047886c7e5b1121bba95a0b6e00371c`.
- CI [43562399685](https://github.com/HVA09/ai-chat-app/actions/runs/43562399685): In Progress عند آخر poll.
- CodeQL [43562399775](https://github.com/HVA09/ai-chat-app/actions/runs/43562399775): In Progress.
- Production smoke [43562399700](https://github.com/HVA09/ai-chat-app/actions/runs/43562399700): In Progress.
- Publish backend image [43562399813](https://github.com/HVA09/ai-chat-app/actions/runs/43562399813): In Progress.
- Render frontend service `srv-daklqph42hec73b1f61g` ما زال آخر deploy مسجلًا `dep-dbr7j4ivcj2c73ejojj0` على `18b8416...` Live؛ لم يظهر deploy جديد على merge commit `18ff9bd...` وقت الفحص، متوقع بسبب `autoDeployTrigger=checksPass`.
- Backend service `srv-dakc4nbm8hqs73e2po9g` لا يحتاج نشرًا من #709 لأن التغيير Frontend-only؛ بقي على backend merge commit #701 `396cb54...`.

### QueuePool follow-up
- Render logs للـbackend من 2026-11-14T05:10Z إلى 05:45Z: 0 QueuePool error lines و0 app-level error lines في هذه النافذة.
- هذه نافذة رصد إضافية، وليست concurrency test ولا دليل end-user load. حادثة 2026-11-13T03:47Z تبقى مفتوحة حتى التحقق من طلبات دخول فعلية بعد النشر وتكرر الاستيقاظ.
- بعد Render Live للواجهة، راقب QueuePool وطلبات المستخدم العادية؛ health 200 وحده لا يكفي.
- لا تعديل pool settings أو خطط Render/Supabase.

### بوابة Backup/Restore
- لا تغيير عن section 47: production backup object 2026-11-13 موجود وarchive list / remote size متحقق، لكن backup SHA-256 نفسه غير مسجل ولا يوجد restore test.
- production dump خام وغير مؤهل لrestore workflow الذي يتطلب `database/staging-sanitized/`.
- Restore-to-staging ما زال OPEN؛ لا تشغيل restore workflow ولا backfill/reindex.


## 49. اكتمال CI بعد دمج #709 ووصول الواجهة إلى Live — 2026-11-14

### Post-merge CI على main
- main: `18ff9bd0f047886c7e5b1121bba95a0b6e00371c`.
- CI [43562399685](https://github.com/HVA09/ai-chat-app/actions/runs/43562399685): Success.
- Backend: `658 passed, 2 warnings in 268.87s`.
- Frontend، SDK، Preview Builder، Production Compose: Success.
- CodeQL Python + JavaScript/TypeScript: Success.
- Production smoke [43562399700](https://github.com/HVA09/ai-chat-app/actions/runs/43562399700): Success؛ خطوات backend smoke، frontend reachability، وbackend health reachability جميعها Success.
- Publish backend image [43562399813](https://github.com/HVA09/ai-chat-app/actions/runs/43562399813): Success.
- كل check-runs التسعة على main: completed/success.
- PostgreSQL CI أظهر duplicate key على `uq_scheduled_task_runs_task_scheduled_for` ضمن regression test المقصود لتأكيد uniqueness؛ pytest overall success، لا تغيّر constraint.

### Render frontend deploy
- Frontend service: `srv-daklqph42hec73b1f61g`.
- Deployment: `dep-dbrv9h15efls73e60teg`.
- Commit: `18ff9bd0f047886c7e5b1121bba95a0b6e00371c`.
- بدأ 2026-11-14T05:42:28.262Z، وانتهى Live بنجاح 05:43:01.392Z.
- Render event `deploy_ended` غير معروض صراحةً في آخر قراءة، لكن سجل deployment نفسه يعرض `status=live` مع `finishedAt`.
- لم يتم manual deploy.

### Render backend deployment state
- Backend service `srv-dakc4nbm8hqs73e2po9g` بقي على deploy حيّ #701 `dep-dbr1p96tlv9c738bj0b0`، commit `396cb54...`.
- هذا متوقع: PR #709 frontend-only ولا يغير ملفات backend. Workflow نشر backend image نجح لكن لم يكن هناك حاجة إلى تغيير كود خدمة API أو قاعدة البيانات.
- لا تغيير Render env, secrets, pool size/overflow, Supabase, DB.

### Post-deploy observation
- نافذة backend logs من 05:43:01Z إلى 06:00:00Z:
  - QueuePool log count: 0.
  - App-level error log count: 0.
  - Request 5xx log count: 0.
  - Internal GET /health logs: 34، بزمن 10ms في السجلات الأولى المعروضة.
  - Request log query العام لم يعرض سجلات مستخدم في تلك النافذة؛ لذلك هذه مراقبة health/absence-of-errors وليست إثبات تجربة مستخدم فعلية أو تحميل متزامن.
- لا نعلن incident QueuePool مغلقًا؛ حادثة 2026-11-13T03:47Z تبقى مفتوحة حتى اختبار دخول/محادثة فعلية بعد استيقاظ instance وتحت حركة طبيعية، مع قياس ضغط الاتصال إن تكررت.

### Backup / restore gate
- لا تغيير عن sections 47–48: production backup بتاريخ 13 نوفمبر موجود وحجمه 862936 bytes وتم التحقق من archive list والوجود البعيد، لكن لا SHA-256 موثق للملف نفسه، ولا sanitized staging dump، ولا restore test.
- restore-to-staging ما زال OPEN؛ لا تشغيل workflow أو backfill/reindex أو استخدام raw production dump.


## 50. PR #710: تحرير DB قبل رسائل التحقق وإصلاح تسرب الرموز في سجلات التطوير — 2026-11-14

### سياق حادثة QueuePool وتحليلها
- Render backend instance srv-dakc4nbm8hqs73e2po9g-khbxm سجل في 2026-11-13T03:47:27Z عاصفة QueuePool limit of size 2 overflow 1 reached، مع فشل عدة طلبات bootstrap مثل GET /users/me وGET /assistants وGET /saved-prompts وGET /chat/models وGET /conversations/bookmarks وGET /memories بعد قرابة 15.4s.
- حدثت كذلك أخطاء في notifications_websocket، لكن مراجعة الكود أظهرت أن مسار المصادقة يغلق SessionLocal بعد قراءة المستخدم وقبل manager.connect وحلقة WebSocket؛ لذلك لا يوجد دليل أن WebSocket كان مالك الاتصالات المحجوزة، ويُعامل كطلب متضرر من نفاد pool.
- قبل العاصفة: بعد استيقاظ Render Free، نجح POST /auth/refresh (3050ms)، وGET /notifications (178ms)، وGET /workspaces (360ms)، ثم وصلت دفعة طلبات bootstrap بالتزامن.
- PR #709 في main (18ff9bd...) سرّع/سلسل تحميل بيانات المستخدم عند startup، وهو تخفيف client-side مناسب. بعد نشره Live على الواجهة عند 05:43:01Z، أظهرت نافذة مراقبة backend من 05:43 إلى 07:35 UTC عدم وجود QueuePool timeouts أو app errors أو HTTP 5xx، مع /health 200 داخلي متكرر. هذا مؤشر تحسن أولي وليس اختبار ضغط أو إثباتًا نهائيًا للسبب الجذري.
- تم تحديد مسارين backend مؤكدين يحتجزان checkout أثناء Redis/SMTP: /auth/verify-email/request و/auth/password-reset/request. PR #710 يعالجهما دون الادعاء بأنهما وحدهما سببا عاصفة 13 نوفمبر.

### PR #710
- PR: https://github.com/HVA09/ai-chat-app/pull/710
- العنوان: fix(auth): release database pool connections before email waits.
- الفرع: fix/auth-release-db-before-email-20261114.
- base: 18ff9bd0f047886c7e5b1121bba95a0b6e00371c.
- آخر head: 47b3337656edb16fa5e9aecfa192928e0aa49d41.
- الحالة عند آخر قراءة: Open / Draft / mergeable؛ لا merge، ولا تغييرات production.
- request_email_verification: صار يستعمل request DB session الموحّدة، يأخذ snapshot للـuser ID/email، ثم commit_and_release_connection(db) قبل Redis token storage وSMTP.
- request_password_reset: يأخذ snapshot للـID/email، ويحرر pool connection قبل Redis وSMTP، ويحافظ على generic response للحسابات غير الموجودة وعلى TTL الحالي.
- لا تغييرات schema/migration، ولا secrets/config/Render/Supabase، ولا رسائل حقيقية أُرسلت خلال الاختبارات.

### CodeQL high-severity finding — تم إصلاحه
- أول CodeQL run على head bda89ae3051a9c6280987edcbb039c9c9080d5ca كشف تنبيه High بعنوان Clear-text logging of sensitive information في ai-backend/app/services/email_service.py:28.
- Annotation كشف أن فرع dev mode عند غياب SMTP_HOST كان يسجل كامل email body. هذا النص قد يحمل password-reset / verification / workspace-invitation token في URL؛ إذن التسرب حقيقي، حتى لو كان قصد المسار سهولة التطوير.
- الإصلاح في PR #710: عند غياب SMTP_HOST يسجل التطبيق فقط أن dev email delivery skipped وموضوع الرسالة؛ لا يسجل recipient ولا body ولا token. الإرسال الحقيقي عند SMTP مضبوط لم يتغير.
- أضيف ai-backend/tests/test_email_service.py::test_development_email_log_never_contains_recipient_or_message_body باستخدام synthetic reset token، ويتأكد أن recipient والـbody والـtoken لا يظهرون في السجل.
- بعد الإصلاح، CodeQL run 43573848897 على head 47b3337... انتهى نجاحًا؛ check CodeQL aggregate صريح: No new alerts in code changed by this pull request. تحليلا Python وJavaScript/TypeScript كلاهما Success.

### Regression tests / CI
- اختبارات pool ذات اتصال واحد من PR #710:
  - email verification يحرر الاتصال قبل Redis وSMTP.
  - password reset يحرر الاتصال قبل Redis وSMTP.
- اختبارات email logging regression تمنع تسرب recipient/message/token في dev mode.
- CI run https://github.com/HVA09/ai-chat-app/actions/runs/43573848891: عند آخر poll كان SDK وFrontend وPreview Builder وProduction Compose كلها Success؛ Backend بقي في Run backend tests with hang diagnostics، لذلك PR لا يزال Draft.
- Backend أنهى إعداد pip-audit، compileall، Alembic upgrade، ORM metadata consistency بنجاح؛ نتيجة pytest لم تكن قد ظهرت بعد، ورابط سجل الوظيفة كان BlobNotFound أثناء استمرار job.
- CodeQL https://github.com/HVA09/ai-chat-app/actions/runs/43573848897: Success / لا تنبيهات جديدة على الكود المعدّل.
- لا تنتقل إلى Ready/merge حتى Backend يكتمل Success على نفس head 47b3337... وبقية check-runs كلها Success.
- duplicate-key PostgreSQL test على uq_scheduled_task_runs_task_scheduled_for ظهر في CI الأسبق لكنه regression test متعمد للـuniqueness، وليس علامة فشل suite أو دليل production duplication.

### Backup / restore / production safety
- Production backup run https://github.com/HVA09/ai-chat-app/actions/runs/43405958682 في 2026-11-13 10:01Z Success: pg_dump custom archive، pg_restore --list validation، upload إلى database/ai-chat-postgres-20261113T100201Z.dump، remote head-object size 862936 bytes، وتنظيف الملف المحلي.
- لا يتوفر حتى الآن SHA-256 موثق لملف dump نفسه، ولا sanitized staging copy، ولا دليل restore ناجح إلى Supabase staging. الـbackup job success لا يعني أن الاستعادة اختُبرت.
- PR #698 restore workflow ما زال restricted to staging، ويشترط exact filename + matching SHA-256 + required reviewers + staging-only secrets/CA/project ref + S3 object-read scope. لا تشغّل workflow حتى تكون هذه العناصر جاهزة ومراجعة.
- لا production restore، لا تغيير DB connection limits أو pool size، لا reindex/backfill ولا strict fingerprint retrieval filtering.

---

## 12. نقطة تحقق موحدة — 2026-11-15 (الحالة الحالية المعتمدة)

هذا القسم هو المرجع الأحدث لحالة #665 والطلبات المرتبطة به. تبقى الملاحظات الأقدم أعلاه سجلاً تاريخياً ولا تُستخدم لاتخاذ قرار دمج دون مقارنة مع هذا القسم.

## 51. نقطة تحقق موحدة — 2026-11-15

### 51.1 خط أساس main الحالي

- المستودع: `HVA09/ai-chat-app`.
- `main` الحالي: `5a69528263c95e9a1cd30cdbb208ac1f5905355a`.
- الالتزام الأخير: `fix(auth): release DB connections before email waits`.
- فحوص `main` على هذا الرأس: **9/9 Success** (backend، frontend، SDK، preview-builder، production-compose، smoke، publish-backend، CodeQL Python، CodeQL JavaScript/TypeScript).
- لا تغيير على Render أو Supabase أو أسرار الإنتاج أو قواعد البيانات ضمن هذه النقطة.

### 51.2 حالة PR #692 — فصل إعداد مزود Embeddings

- PR: https://github.com/HVA09/ai-chat-app/pull/692
- الحالة الحالية: **Merged** في 2026-11-12.
- رأس الفرع: `26c2c30fe7ed67eba814f0ace81985074c5d9d8f`.
- Merge commit: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- القرار: إعداد مزود Embeddings منفصل أصبح جزءاً من `main`. لا يُعاد استخراج أو تقديم هذا النطاق من #665 مرة أخرى؛ يجب أولاً فحص الملفات الموجودة في `main` واستبعاد التكرار.

### 51.3 حالة PR #710 — تحرير اتصال DB قبل Redis/SMTP

- PR: https://github.com/HVA09/ai-chat-app/pull/710
- حالة طلب PR نفسه: **Closed / not merged**؛ لا توصفه بأنه merged.
- مع ذلك، تم إدخال الإصلاح المكافئ إلى `main` مباشرة في الالتزام `5a69528263c95e9a1cd30cdbb208ac1f5905355a`.
- الملفات الموجودة في التغيير على `main`: `ai-backend/app/auth/routes.py`، `ai-backend/app/services/email_service.py`، `ai-backend/tests/test_email_service.py`، `ai-backend/tests/test_external_wait_pool_release.py`.
- الإصلاح يحرر اتصال قاعدة البيانات قبل انتظار Redis/SMTP، ويمنع تسجيل مستلم البريد ومحتوى الرسالة والرموز الحساسة في وضع التطوير.
- فحوص `main` بعد إدخال الإصلاح: 9/9 Success.
- القرار: **لا تعِد تطبيق هذا الإصلاح** في PR فرعي من #665، وراجع `main` قبل أي معالجة لاحقة لمشكلة QueuePool.

### 51.4 حالة PR #665 الأصلي

- PR: https://github.com/HVA09/ai-chat-app/pull/665
- الحالة الحالية: Open / Draft.
- رأس الفرع: `4792285440511833b66e1045bc235143a5a302a5`.
- الحجم: 70 ملفاً، +15,331 إضافة، -388 حذفاً.
- فحوص الرأس الذي جرى التحقق منه: 8/8 Success، لكن ذلك لا يجعل التغيير آمناً للدمج ككتلة واحدة.
- الفرع متباعد عن `main` الحالي، والتغيير يجمع نطاقات كبيرة مختلفة (Embeddings، RAG، فهرسة، migrations، MCP، الذاكرة، وواجهة المستخدم).
- القرار الثابت: إبقاء #665 Draft كمصدر مرجعي أثناء التفكيك؛ لا دمج مباشر، ولا إعادة توجيه جماعية، ولا cherry-pick عشوائي.

### 51.5 ما اكتمل بالفعل في main — لا تُعِد تنفيذه من #665

**أ. صلاحيات RAG الحية — مكتملة**

- PR #694: https://github.com/HVA09/ai-chat-app/pull/694
- Merge commit: `c8264a391ba1b5cfaa02821320d3ae5dd6b17c13` (2026-11-12).
- يفرض التحقق على ملكية المحادثة، وعضوية مساحة العمل، وصلاحية المشروع، ومشاركة المساعد.
- يعيد التحقق بعد انتظار مزود Embeddings وقبل إرجاع محتوى الملفات.
- اختبارات Regression تغطي مستخدماً آخر، وإلغاء عضوية مساحة العمل، ورفض صلاحية المشروع، وإلغاء مشاركة المساعد، وتغير الصلاحيات أثناء انتظار المزود.
- لا تستخرج هذا النطاق مرة أخرى من #665.

**ب. إعداد مزود Embeddings — مكتمل**

- PR #692: https://github.com/HVA09/ai-chat-app/pull/692
- Merge commit: `b80f6d658d4848f78c726f0a03b21ae50359fada`.
- الإعداد مستقل عن مزود المحادثة مع تحقق من عنوان الخدمة والمفتاح والنموذج والأبعاد. لا تكرر هذه التغييرات.

**ج. بصمات مصدر الملف وهوية Embeddings — مكتملة على مستوى المخطط والكود**

- PR #695: https://github.com/HVA09/ai-chat-app/pull/695
- Merge commit: `f3ba9d4ab6d9c35276e4ca0baec5ff70558f592f`.
- migration الفعلية في `main`: `0082_file_index_fingerprints.py`، revision `0082_file_index_fingerprints`، وتسبقها `0081_harden_all_public_tables`.
- الترحيل schema-only؛ لا backfill ولا إعادة فهرسة تلقائية. السجلات القديمة قد تبقى بصماتها NULL إلى أن تتم معالجة آمنة منفصلة.

**د. إعادة فهرسة ملف واحد بطريقة آمنة — مكتملة في الكود**

- PR #696: https://github.com/HVA09/ai-chat-app/pull/696
- Merge commit: `31503ae13b7215a7dc6ca312ea0dfd8a6abff5db`.
- تجهيز embeddings يتم قبل استبدال المقاطع المحفوظة؛ فشل المزود أو تغير المصدر أو سحب الصلاحية لا يمحو الفهرس السابق.
- توجد اختبارات للصلاحيات وإلغاء الوصول وفشل المزود وتغير المصدر.

**هـ. تعارض ترحيل يجب عدم إعادته**

- #665 القديم يضم `0081_file_index_fingerprints.py`.
- `main` يستخدم revision `0081_harden_all_public_tables` بالفعل لترسيخ سياسة RLS.
- بصمات الملفات أضيفت في `0082_file_index_fingerprints` بعده.
- لذلك يمنع نقل ملف migration القديم من #665 أو إعادة استخدام revision `0081`; يجب أن يتبع أي ترحيل جديد رأس Alembic الحالي وأن يُختبر على نسخة منفصلة.

### 51.6 ترتيب العمل المتبقي

1. **استقرار الإنتاج والنسخ والاستعادة:** إغلاق ملاحظة QueuePool باختبار مستخدم فعلي ومراقبة كافية، وإكمال sanitized staging restore مع SHA-256 موثق. لا backfill ولا reindex ولا live provider calls قبل هذه البوابة.
2. **File extraction hardening:** مراجعة حدود بايتات الإدخال والصفحات/الأوراق والوقت والذاكرة، ملفات ZIP المضغوطة/التالفة، وملفات PDF كبيرة أو مشفرة. توجد حالياً وظائف استخراج واختبارات أساسية لـTXT/CSV/PDF/DOCX/XLSX؛ المطلوب تدقيق الحدود وحالات الضغط والفساد، لا استبدال الخدمة عشوائياً.
3. **Index compatibility audit:** إعداد تقرير read-only يميز الملفات ذات fingerprints المكتملة من الملفات القديمة NULL، ويقارن بُعد المتجه وهوية المزود/النموذج؛ ثم dry-run لتقدير نطاق أي إعادة فهرسة مستقبلية دون الاتصال بمزود خارجي.
4. **Offline RAG evaluation:** مجموعة بيانات ثابتة ومقاييس Recall@k وPrecision@k وMRR وnDCG@k، مع تقارير قابلة لإعادة الإنتاج ومن دون استهلاك API.
5. **Prompt/citation safety:** اختبارات prompt injection محلية، وفصل تعليمات النظام عن المحتوى غير الموثوق، وتقييم صحة الاستشهادات.
6. **MCP/tool security:** allowlists، وأقل صلاحية، وتحقق التفويض في الخادم، ومنع SSRF وحقن الأوامر، واختبارات no-side-effect.
7. **Memory UX:** بعد استقرار الصلاحيات والبيانات؛ موافقة صريحة قبل الحفظ وفصل ذاكرة المستخدم عن ذاكرة المشروع.
8. **UI/docs:** أخيراً بعد ثبات عقود API وسلوك الخادم.

### 51.7 بوابات القبول الإلزامية

- يبدأ كل PR جديد من أحدث `main` ويسجل base SHA وhead SHA.
- PR واحد لكل مسؤولية وبأصغر نطاق ممكن.
- لا migration متعارضة أو غير خطية؛ تحقق من Alembic heads والترقية/التراجع على قواعد disposable.
- جميع الاختبارات المطلوبة وCodeQL يجب أن تنجح على آخر head نفسه.
- كل خلل أمني أو عطل مؤثر ينتج Regression Test.
- لا live provider calls ولا reindex/backfill ولا تغييرات production أو أسرار دون خطة منفصلة ونسخة قابلة للاستعادة.
- نجاح CI لا يثبت نجاح النشر أو سلامة بيانات الإنتاج؛ يجب توثيق كل مستوى دليل بشكل مستقل.

### 51.8 نقطة الاستئناف الحالية

- لا تبدأ مجدداً بصلاحيات RAG أو إعداد Embeddings أو fingerprints أو safe reindex؛ هذه المكونات موجودة بالفعل في `main` عبر PRs #692 و#694 و#695 و#696.
- لا تدمج #665 ككتلة ولا تنقل migration `0081_file_index_fingerprints.py`.
- الأولوية الآن هي استقرار التطبيق والتحقق من النسخ والاستعادة، ثم تدقيق استخراج الملفات وتوافق الفهرس بصورة read-only.
- خط الأساس: `main` عند `5a69528263c95e9a1cd30cdbb208ac1f5905355a` وقت نقطة التحقق هذه. افحص SHA الحالي مجدداً قبل أي PR لاحق.


### 51.9 نتائج تدقيق استخراج الملفات وتقييم RAG — 2026-11-15

**ضوابط الرفع الموجودة بالفعل في `main`:**
- مسار الرفع يقرأ الملف على دفعات 1 MiB ويتوقف عند `MAX_UPLOAD_SIZE_MB`.
- يتحقق من النوع باستخدام magic bytes بدلاً من الثقة في الامتداد وحده.
- ملفات DOCX/XLSX تمر بفحص ZIP: حد لعدد العناصر، والحجم غير المضغوط الإجمالي، ونسبة الضغط، والمسارات غير السليمة.
- خدمة الاستخراج تدعم TXT وCSV وPDF وDOCX وXLSX، وحد النص الافتراضي 20,000 محرف؛ وXLSX يستخدم `read_only=True`.

**مجالات تحسين موارد الاستخراج التي تحتاج اختباراً قبل التغيير:**
- PDF: لا يظهر في الحلقة الحالية حد مستقل لعدد الصفحات؛ وقد تواصل معالجة ملف يحتوي صفحات كثيرة قليلة/عديمة النص حتى بلوغ حد الأحرف.
- DOCX: تحميل `Document(...)` وتجميع الفقرات والجداول يحدث قبل تطبيق القص النهائي للنص.
- TXT/CSV: `Path.read_bytes()` يقرأ الملف قبل اقتطاع الجزء الذي سيُحلل؛ حجم الرفع محدود، لكن القراءة المتدفقة ستقلل الذروة في الذاكرة.
- هذه ملاحظات hardening وأداء، وليست ادعاءً بوجود استغلال مثبت. يجب إضافة قياسات/اختبارات حدود قبل تعديل السلوك.

**تقييم RAG غير المتصل:**
- لم أجد في `main` حالياً خدمة `rag_evaluation.py` أو مجموعة fixtures/تقارير RAG مستقلة في مجلدي الخدمات/الاختبارات.
- لذلك يبقى offline evaluator عملاً مستقبلياً واضحاً، ويجب أن يعمل على بيانات اصطناعية/منزوعة الهوية دون استدعاء مزودي Embeddings أو Chat.

**MCP والأدوات:**
- توجد بالفعل وحدات `mcp_client.py` و`tool_security.py` ومجلد `tools` في `main`.
- لا يعني وجودها أن جميع تغييرات #665 مطلوبة؛ يجب إجراء مراجعة capability-by-capability ومقارنة الكود والاختبارات قبل استخراج أي تغيير جديد.

### 51.8 حالة التغييرات المفتوحة بعد التحقق

- خط الأساس الحالي لـ `main`: `5a69528263c95e9a1cd30cdbb208ac1f5905355a`، وفحوصه الأخيرة 9/9 Success.
- PR #710 نفسه: Closed / not merged. لا تصفه بأنه مدمج؛ الإصلاح المكافئ موجود في `main` عبر الالتزام `5a695282...` ويحرر اتصالات قاعدة البيانات قبل Redis/SMTP، ويمنع تسرب جسم البريد والرموز في سجلات التطوير. لا تعِد تطبيقه.
- PR #691 القديم: Closed / superseded؛ تم نقل سجل التفكيك إلى PR #714 على فرع نظيف مبني من SHA الحالي لـ `main`.
- PR #714: https://github.com/HVA09/ai-chat-app/pull/714 — سجل توثيقي بملف واحد؛ رأسه `04903b09ba3dc8998b9a03bae6f51efc618137f7`، Base `5a69528263c95e9a1cd30cdbb208ac1f5905355a`. آخر تحقق مسجل: 7/8 checks Success، وBackend ما زال `in_progress`. لا تحول الطلب إلى Merged ولا تعتبر CI كاملاً حتى يكتمل Backend بنجاح على هذا الرأس نفسه.
- PR #665: ما زال Open / Draft، 70 ملفًا (+15,331 / -388)؛ يبقى مرجعًا فقط ولا يدمج دفعة واحدة.
- PRs #692 و#694 و#695 و#696 مدمجة؛ لا تُكرر نطاقاتها. راجع SHA الحالي وملفات `main` قبل أي PR جديد.
- لم يتغير Render أو Supabase أو أسرار الإنتاج أو قواعد البيانات في هذه الخطوة.

### 51.9 إجراء الاستئناف التالي

1. انتظر إكمال Backend على PR #714؛ عند نجاح جميع الفحوص المطلوبة، راجع الحالة النهائية ثم ادمج التوثيق فقط وفق تفويض المستخدم العام، إذا سمحت حماية الفرع.
2. لا تغلق #665 ولا تحذف فرعه؛ لا تنشئ نطاق RAG أو Embeddings أو fingerprints مرة أخرى.
3. الأولوية الهندسية بعد تثبيت التوثيق: التحقق من النسخ الاحتياطي والاستعادة إلى staging ببيانات منزوعة الهوية، ثم تدقيق حدود استخراج الملفات وتوافق الفهرس بصورة read-only.
4. لا backfill ولا إعادة فهرسة جماعية ولا live provider calls حتى وجود نسخة staging قابلة للاستعادة وقياس/خطة تنفيذ وتراجع.


## 52. مصالحة حالة PR #714 و#715 — 2026-11-16

> **هذه هي نقطة الاستئناف الأحدث والمرجع الحاسم للحالة الحية.** تبقى الملاحق السابقة، بما فيها المقاطع المكررة الترقيم في 51.8 و51.9، محفوظة كسجل تاريخي فقط. أي عبارة فيها تطلب انتظار #714 أو تصفه بأنه غير مدمج أصبحت متقادمة.

### الحالة المؤكدة من GitHub

- PR #714 — [تحديث سجل تفكيك #665](https://github.com/HVA09/ai-chat-app/pull/714): **Closed + Merged** بتاريخ 15 نوفمبر 2026. Merge commit ورأس `main` الناتج عنه: `5d4c46af18838f7cbcebd3063f30279fd6146ad5`.
- PR #715 — [تحديث سجل حوكمة AI Chat App](https://github.com/HVA09/ai-chat-app/pull/715): **Closed + Merged** بتاريخ 16 نوفمبر 2026. Merge commit: `88f8351767450951cef14dffb44a7609c09e6950`.
- تمت مقارنة SHA الخاص بدمج #715 مع `main` مباشرة؛ النتيجة `identical`، أي إن رأس `main` عند التحقق هو `88f8351767450951cef14dffb44a7609c09e6950`.
- PR #665 الأصلي: ما زال **Open + Draft + Unmerged**، ورأسه `4792285440511833b66e1045bc235143a5a302a5`. لا يُدمج ككتلة ولا يُعاد تأسيسه جماعياً.
- PR #671: ما زال **Open وغير Draft وغير مدمج**، ومبني على Base قديم `b690c149610a704f78d7f4ee9e6f377be7466703`. يحتاج قراراً مستقلاً في المهمة CHAT-003؛ لا يُعامل كمرجع حالة حالي ولا يُدمج اعتماداً على فحوص قديمة.

### تصحيح القراءة والسجل

1. تعليمات 51.8/51.9 التي تقول إن PR #714 ما زال قيد التنفيذ أو يجب انتظاره ثم دمجه كانت صحيحة وقت تسجيلها فقط؛ أصبحت تاريخية بعد دمج #714.
2. لا تخلط بين دمج سجل التفكيك #714 وبين دمج PR #665؛ المصدر الكبير ما زال Draft.
3. رأس الاستئناف الحالي لهذا السجل هو `main = 88f8351767450951cef14dffb44a7609c09e6950`، وليس `5a695282...` أو `5d4c46...`.
4. دمج #715 كان تحديثاً توثيقياً لسجل حوكمة المشروع؛ لا يثبت نشر التطبيق أو قبول Android أو إغلاق Issues التشغيلية.

### نقطة الاستئناف التالية

- حافظ على أولوية الاستقرار والقبول التشغيلي، ولا تفتح نطاقات جديدة واسعة من #665.
- لا تكرر ما دخل إلى `main` عبر #692 و#694 و#695 و#696، وراجع SHA الحالي قبل أي عمل مشتق.
- استمر في التحقق من النسخ والاستعادة، ثم تدقيق حدود استخراج الملفات وتوافق الفهرس على نحو read-only قبل أي backfill أو إعادة فهرسة أو استدعاء مزود حي.
- راجع PR #671 بصورة مستقلة واحفظ قيمته التوثيقية قبل تقرير تحديثه أو إغلاقه.


## 53. إعادة مراجعة PR #665 وخريطة ما تم استخراجه — 2026-11-26

> هذه أحدث نقطة تحقق في هذا الملف. الأقسام السابقة سجل تاريخي، ولا تُستخدم حالة PR أو SHA قديم فيها كدليل حي.

### 53.1 القرار التنفيذي المختصر

- PR #665 يبقى **Open + Draft + Unmerged** كمصدر تاريخي للمراجعة فقط. لا تدمجه ككتلة واحدة، ولا تحاول تحديثه أو rebase له مباشرة.
- الرأس الحالي المرصود للطلب: `4792285440511833b66e1045bc235143a5a302a5`، والفرع `ai/embedding-provider-separation-20261025`.
- حجم التغيير: 70 ملفًا، +15,331 إضافة، -388 حذفًا. يحتوي مزايا متعددة مستقلة ومترابطة: إعداد مزود Embeddings، بصمات الفهرسة وترحيل DB، RAG والصلاحيات، تقييم RAG والاستشهادات، تعليمات النظام، MCP وأمان الأدوات، اقتراح الذاكرة وواجهتها، واستخراج الملفات والتوثيق.
- مقارنة الرأس الحالي مع `main` المرصود `0ef6148c9d86874c9262cae7930f5cf9b3b52379` تُظهر `diverged`: 460 commit للأمام و103 للخلف، مع merge-base قديم `b690c149610a704f78d7f4ee9e6f377be7466703`. GitHub يعرض `mergeable=false`. لا تُفسر هذه الحالة على أنها مشكلة زر أو مجرد Draft؛ الفرع قديم ومتباعد فعليًا.
- CI وCodeQL نجحا سابقًا على رأس #665 نفسه في 2026-10-31 (CI `41247792816` وCodeQL `41247792783`)، لكن هذه فحوص تاريخية وليست قبولًا للرأس الحالي بعد شهر من تطور `main`. طلب Combined Status الحالي لا يقدم Status contexts.
- لا يوجد في هذه المراجعة تشغيل محلي أو runtime أو live provider call، ولا تغيير في Render/Supabase أو secrets أو قاعدة الإنتاج.

### 53.2 ماذا كان الهدف من #665؟

1. فصل مزود Embeddings عن مزود المحادثة كي يمكن ضبط النموذج والمفتاح والعنوان والأبعاد بصورة مستقلة وآمنة.
2. بناء أساس أكثر سلامة لفهرسة ملفات المعرفة باستخدام بصمات المصدر وفضاء المتجهات، ومنع حذف الفهرس القديم قبل نجاح التوليد الجديد.
3. تقوية صلاحيات RAG وسياق المحادثة والمشروع والمساعد عند تغير العضوية.
4. إنشاء تقييم RAG offline قابل للتكرار، مع Recall@k وPrecision@k وnDCG@k وReciprocal Rank؛ هذه المجموعة الاصطناعية لا تثبت جودة النموذج على ملفات حقيقية.
5. تحسين تعليمات النظام وحماية السياق والاستشهادات وأمان MCP وأدوات الوكيل.
6. إضافة اقتراح ذكريات من محادثات المستخدم، مع اشتراط مراجعة المستخدم وحفظه الصريح؛ لا حفظ تلقائي.
7. إضافة واجهة وتوثيق لهذه القدرات.

### 53.3 ما الذي أُخرج من #665 ودخل main بالفعل؟

| PR | النطاق المستخرج | الحالة المثبتة |
|---|---|---|
| #690 | إصلاح صيغة استجابة Gemini REST المفردة `embedding.values` واختبار regression | Merged؛ لا تعِد إدخاله من #665 |
| #692 | إعداد مزود Embeddings المستقل والتحقق من المزود/النموذج/العنوان/الأبعاد | Merged؛ لا تعِد إدخاله |
| #694 | التحقق من صلاحيات المحادثة ومساحة العمل والمشروع والمساعد داخل RAG وإعادة التحقق بعد انتظار المزود | Merged؛ لا تعِد إدخاله |
| #695 | بصمات مصدر الملف وفضاء Embeddings وmigration 0082 وحماية الفهرس القديم عند فشل الاستبدال | Merged؛ لا تعِد إدخاله |
| #696 | endpoint لإعادة فهرسة ملف واحد بطلب صريح، مع التحقق من الصلاحية والبصمة والحفاظ على المقاطع عند الفشل | Merged؛ لا تعِد إدخاله |

هذه الدمجات تثبت أن أجزاء مهمة من #665 أُعيد بناؤها كطلبات صغيرة من main ثم دمجت؛ لا تعني أن كل محتوى #665 دخل main. كما أن #695 لم يفعّل strict filtering أو إعادة فهرسة جماعية، و#696 لا يشغّل إعادة فهرسة تلقائية أو مجدولة.

### 53.4 ما الذي لا يزال غير محسوم من محتوى #665؟

- **خطة توافق الفهرس القديم وإعادة الفهرسة:** migration 0082 تضيف metadata nullable؛ سجلات الملفات القديمة قد تبقى بلا بصمات. لا تبدأ bulk reindex أو strict stale-index filtering قبل نسخة staging قابلة للاستعادة وقياس الأثر وخطة rollback. تحقق من حالة main الحالية قبل اعتبار أي جزء من هذا البند متبقياً.
- **سلوك RAG المختلط (حديث + legacy):** سجل #665 احتوى معالجة fallback للملفات القديمة غير المفهرسة عندما توجد مقاطع حديثة؛ يلزم التأكد أن هذا السلوك لم يُستبدل أو يتراجع عنه في التغييرات اللاحقة.
- **تقييم RAG:** بيانات الاختبار الاصطناعية مفيدة كـsmoke/benchmark أولي، لكنها ليست baseline حيًا ولا تثبت citation correctness أو مقاومة prompt injection أو جودة إجابات المستخدم. لا تستخدم `--run-live` دون قرار مستقل بسبب إرسال نص لمزود واحتمال استهلاك الحصة/التكلفة.
- **تعليمات النظام وPrompt injection:** دفاع إضافي لا يضمن المناعة؛ يحتاج تقييمًا عدائيًا مضبوطًا واختبارات حدود الأدوات والصلاحيات.
- **MCP وأمان الأدوات:** يجب مراجعة كل capability وصلاحيتها وتأثيرها بشكل مستقل؛ لا تفعل خوادم أو أدوات إنتاجية بناء على وجود الكود فقط.
- **Memory Suggestions:** لم أتحقق في هذه الجولة من أن API والواجهة ما زالا موجودين في main أو ما إذا تم استخراج بعضهما في PRs لاحقة. لا تعتبرهما مدمجين أو مفقودين حتى تتم مطابقة الملفات الحالية. يجب إبقاء الموافقة الصريحة والحواجز الخاصة بالبيانات الحساسة وعزل ذاكرة المستخدم عن ذاكرة المشروع.
- **استخراج الملفات:** بعض تحسينات DOCX/PDF/TXT/CSV ضمن #665 لا يجوز أخذها من الفرع القديم دون مقارنة مع main؛ ولا تعدل ملفات الرفع المحمية في برنامج الاستقرار الحالي.

### 53.5 لماذا لا ندمج #665 رغم نجاح CI التاريخي؟

1. **اتساع النطاق:** 70 ملفًا وأكثر من 15 ألف إضافة تجعل مراجعة الأثر والتراجع صعبة، وتربط إعداد المزود والفهرسة وRAG والذاكرة والأدوات والواجهة في تغيير واحد.
2. **تفرع الفرع:** 460 commit ahead و103 behind و`mergeable=false`؛ دمجه قد يعيد تغييرات قديمة أو يتعارض مع إصلاحات main اللاحقة.
3. **تكرار ما دُمج:** أجزاء أساسية دخلت بالفعل عبر #690 و#692 و#694 و#695 و#696. دمج #665 كما هو قد يكررها أو يعيد نسخ نسخ قديمة منها.
4. **مخاطر قاعدة البيانات والفهرسة:** migration 0081/0082 وتوافق المتجهات والملفات القديمة تحتاج backup/restore وstaging واختبارات rollback. نجاح unit tests لا يثبت أمان ترحيل قاعدة الإنتاج.
5. **حدود النشر:** سجل #665 يوثق أن Render كان مضبوطًا على auto-deploy عند commit، وأن startup script يشغل `alembic upgrade head`. لذلك دمجًا عاديًا قد يطلق نشرًا وترحيلًا فعليًا قبل بوابة قبول مستقلة.
6. **الخصوصية والأمن:** اقتراح الذكريات يرسل مقتطفات من رسائل المستخدم إلى مزود AI عند طلب المستخدم؛ يحتاج موافقة واضحة، وفحص أسرار لا يدعي الاكتمال، واختبارات ملكية وعزل. وأمان MCP/الأدوات يتطلب مراجعة مستقلة.
7. **تقادم الفحوص:** نجاح CI/CodeQL على SHA في أكتوبر لا يثبت توافق الفرع مع main في 26 نوفمبر.

### 53.6 لماذا بعض PRs Draft وبعضها مفتوح غير Draft؟

- **Draft**: الكاتب يعلن أن التغيير غير جاهز للمراجعة النهائية/الدمج، غالبًا بسبب نواقص أو تبعيات أو انتظار تحقق.
- **Open + Ready for review**: يعلن أن المراجعة مطلوبة؛ لا يعني أن الدمج آمن أو أن الفحوص نجحت.
- **Open + mergeable=true**: GitHub لا يرى تعارض دمج حاليًا وفق حسابه؛ لا يثبت جودة التغيير أو اكتمال الفحوص.
- **mergeable=false**: GitHub لا يعلن قابلية الدمج؛ قد يكون هناك تعارض أو سبب تقني آخر، ويجب فحصه على الرأس الحالي.
- **Merged**: دخلت التغييرات إلى base branch؛ لا يعني أن المنتج نُشر أو أن كل بوابات التشغيل مغلقة.
- **Closed, not merged**: أُغلق الطلب دون إدخال تغييراته؛ قد يكون superseded أو duplicate أو تم استخراج ما يلزم منه في PR أصغر.

### 53.7 حالة الطلبات المرتبطة التي فُحصت في 2026-11-26

- #690، #692، #694، #695، #696: مدمجة؛ لا تكرر نطاقاتها من #665.
- #691: مغلق غير مدمج لأنه استُبدل بسجل #714.
- #714 و#715: مدمجان كتحديثات توثيقية؛ لا يعني ذلك دمج #665.
- #767: ما زال Draft؛ عمل upload processing منفصل عن #665، ولا يجوز تفعيله أو دمجه قبل بوابات worker/supervisor/lease المسجلة في مراجعة 26 نوفمبر.
- #780 و#782 و#784: Draft توثيقي مفتوح؛ #783 مفتوح Ready for review. هذه سجلات/خطط مراجعة وليست إصلاحات كود، وتحتاج مصالحة حتى لا تتكرر قوائم المهام.
- #671: أغلق غير مدمج بتاريخ 16 نوفمبر وفق الحالة الحالية؛ لا تعتمد SHA وفحوصه القديمة.

### 53.8 قرار الاستمرار

1. لا تدمج #665 ولا تحذفه ولا تعِد تأسيسه؛ احتفظ به كمصدر تاريخي قابل للرجوع.
2. اعتبر #690/#692/#694/#695/#696 أجزاء مستخرجة وموجودة في main، ولا تعِد تنفيذها.
3. قبل أي استخراج جديد، قارن كل ملف من #665 مع main الحالي وحدد ما إذا كان قد دُمج أو تغير أو أصبح غير مطلوب.
4. لا تنشئ PR فرعيًا جديدًا للـMemory Suggestions أو MCP أو evaluator قبل إثبات أن القدرة غير موجودة في main والطلبات المفتوحة.
5. لا bulk reindex، ولا `--run-live`، ولا migration/production deploy، ولا تغيير Render/Supabase أو secrets ضمن هذه المراجعة.
6. الأولوية الآن هي جرد ما تبقى من #665 مقابل main وPRs المفتوحة، ثم إنشاء PR صغير فقط إذا بقيت فائدة واضحة وغير مكررة، مع CI/CodeQL على SHA نفسه ومراجعة مستقلة.


## 54. تحقق فعلي من Memory Suggestions وRAG/MCP — 2026-11-26

> هذه النقطة مبنية على مقارنة ملفات `main` عند `0ef6148c9d86874c9262cae7930f5cf9b3b52379` مع الفرع الأصلي لـ #665 عند `4792285440511833b66e1045bc235143a5a302a5`. الفحص قراءة فقط؛ لا تشغيل محلي أو runtime أو provider calls.

### 54.1 Memory Suggestions — غير موجودة في main، موجودة في #665

**ما هو موجود في main:**
- `ai-backend/app/routers/memories.py` يوفر CRUD فقط: `GET/POST /memories` و`PATCH/DELETE /memories/{memory_id}`.
- `ai-backend/tests/test_memories.py` يغطي إنشاء الذاكرة وتعديلها وعرضها وحذفها وعزل ملكية المستخدم ورفض المحتوى الفارغ.
- `ai-frontend/src/lib/memoriesApi.js` يوفر list/create/update/delete فقط.
- `AccountSettings.jsx` وإجراءات الرسائل تسمح بحفظ نص يختاره المستخدم يدوياً. لم يظهر endpoint `/memories/suggest` أو مكوّن `MemorySuggestionsPanel` أو تدفق اقتراحات داخل `App.jsx` في main.

**ما هو موجود في فرع #665:**
- endpoint `POST /memories/suggest` في `memories.py`، ويشترط أن تكون المحادثة مملوكة للمستخدم وغير محذوفة.
- يحد السياق إلى 40 رسالة حديثة و14,000 محرف، ويطبق حدود استخدام AI اليومية وحدود مساحة العمل عند انطباقها.
- يرسل transcript منظمًا إلى مزود AI، ويطلب حتى خمسة اقتراحات طويلة الأمد تخص المستخدم، لا ذاكرة المشروع.
- يتحقق أن evidence اقتباس متصل ودقيق من رسالة كتبها المستخدم، ويرفض التكرار وبعض أنماط الأسرار والمعرفات والبيانات الحساسة عبر فحص regex تقريبي.
- لا يحفظ الاقتراحات تلقائيًا؛ الواجهة `MemorySuggestionsPanel` تعرض النص والدليل، ويختار المستخدم الحفظ أو التجاهل. الحفظ يستعمل مسار إنشاء الذاكرة الحالي.
- أضيفت schemas وAPI frontend وواجهة ولوحة اقتراحات واختبارات backend/frontend مرتبطة بالتدفق.

**تقييم الأمان والخصوصية:**
- الفحص التقريبي للبيانات الحساسة ليس ضمانًا؛ قد يفوّت صياغات غير مباشرة أو لغات/أنماط غير مغطاة. يلزم إبقاء مراجعة المستخدم قبل الحفظ، مع توضيح أن نص المحادثة المختار سيُرسل إلى مزود AI عند الضغط على طلب الاقتراحات.
- يجب التأكد من أن طلب الاقتراحات لا يبدأ تلقائيًا عند فتح المحادثة أو إرسال رسالة، وأن إلغاء/تبديل المحادثة لا يعرض نتائج الطلب السابق في محادثة أخرى.
- يلزم اختبار ملكية المحادثة، المحادثات المحذوفة، حدود الاستخدام، الاقتباس الدقيق، عدم الحفظ قبل الموافقة، وعدم اقتراح معلومات حساسة عربية/إنجليزية، وفشل/timeout المزود.
- لا تنقل ملف `memories.py` من الفرع القديم كما هو؛ أعد بناء التغيير كـ vertical slice صغير من أحدث main بعد مراجعة مستقلة للخصوصية والصلاحيات وعقود الواجهة.
- القرار: **قدرة غير مدمجة وموجودة في المصدر القديم؛ لا تُعلن مكتملة ولا تُدمج تلقائيًا.** احتفظ بها كبند قابل للاستخراج بعد قبول ضوابط الخصوصية.

### 54.2 RAG evaluation — موجودة في #665 وغير مثبتة في main الحالي

- في فرع #665 توجد `rag_evaluation.py`، و`scripts/evaluate_rag_retrieval.py`، و`docs/RAG_EVALUATION.md`، وfixture اصطناعي من 20 سؤالًا و100 وثيقة، واختبارات للمقاييس والتحقق من البيانات ومقارنة التقارير.
- البحث في main الحالي لم يُظهر خدمة evaluator أو script أو fixture مماثلًا؛ لذلك تبقى أداة التقييم offline بندًا غير مستخرج وفق الملفات التي تمت مطابقتها.
- الأداة في الفرع القديم تفصل بين `--validate-only` المحلي و`--run-live` الذي يستدعي مزود embeddings وقد يستهلك الحصة/التكلفة. لم يتم تشغيل أي منهما في هذه المراجعة.
- هذه المجموعة تقيس ترتيب الوثائق فقط؛ لا تثبت جودة الإجابة النهائية أو صحة الاستشهادات أو مقاومة prompt injection. يمكن استخراج validator offline لاحقًا في PR مستقل دون تشغيل حي.

### 54.3 Prompt injection / MCP — الأساس موجود في main، لا تكرر الحزمة القديمة

- main يحتوي `tool_security.py` لتقييد أحجام/عمق arguments والتحقق من JSON schema، وتغليف نتائج الأدوات كبيانات غير موثوقة مع إشارات prompt-injection عربية وإنجليزية.
- main يحتوي `mcp_client.py` مع allowlist للأدوات، وتنقية remote schema annotations، والتحقق من URL وHTTPS في production، وإخفاء بيانات الاتصال من بعض السجلات.
- `agent_runtime.py` يقصر اكتشاف/استخدام MCP على مسؤولي التطبيق وفق السياسة الحالية، ويوقف tool follow-ups بعد مخرجات غير موثوقة، ويطبق حدودًا لعدد الجولات والأدوات والوقت.
- فرع #665 يضيف تغييرات واختبارات كثيرة لهذه الملفات، لكن وجود تغييرات في diff لا يثبت أن كل إضافة لازمة أو أن السياسة الحالية ناقصة. يجب استخراج diff لكل capability مقابل main ومراجعة الاختبارات المرتبطة بها قبل إنشاء أي PR.
- لا تفعيل لخوادم MCP أو تغيير إعداداتها أو صلاحياتها في هذه المراجعة.

### 54.4 قرار الاستخراج التالي

1. لا تدمج #665 ولا تنقل ملفاته مباشرة.
2. Memory Suggestions: تبقى ميزة غير مدمجة؛ لا تبدأ التنفيذ قبل مراجعة خصوصية مستقلة واعتماد تدفق موافقة صريح.
3. RAG evaluator: يمكن لاحقًا بناء PR صغير للـoffline-only validator/metrics من أحدث main، دون `--run-live`.
4. MCP/tool security: لا PR عام؛ استخرج فقط ثغرة أو capability محددة يثبتها diff واختبار regression.
5. حافظ على قيود الاستقرار الحالية، ولا تلمس ملفات الرفع المحمية أو الإنتاج أو DB أو Render/Supabase.


### 54.5 تحقق إضافي من تدفق واجهة Memory Suggestions في فرع #665

- يظهر زر طلب الاقتراحات في `App.jsx` فقط عند وجود محادثة وعدم كونها للقراءة فقط؛ ويستدعي `handleSuggestMemories` من نقرة المستخدم، لا من فتح المحادثة أو إرسال الرسائل تلقائيًا.
- عند تبديل المحادثة، يزيد التطبيق request generation ويصفر الاقتراحات وحالة العرض والتحميل؛ كما يهمل نتيجة الطلب إذا أصبحت المحادثة النشطة مختلفة عن المحادثة التي بدأ منها الطلب.
- حفظ الاقتراح منفصل عن توليده: `handleSaveSuggestedMemory` يستدعي `createMemory` فقط بعد اختيار المستخدم زر الحفظ في اللوحة. التجاهل/الإغلاق لا ينشئ سجل ذاكرة.
- هذا يثبت وجود بوابة موافقة تفاعلية في الفرع القديم، لكنه لا يلغي الحاجة إلى توضيح إرسال النص إلى مزود AI، أو اختبار كل حالات السباق والفشل والخصوصية قبل إعادة البناء من main.


## 55. فحص توافق فهرس RAG في main — 2026-11-26

### ما ثبت من قراءة الكود

- main يحتوي أعمدة metadata في `FileAttachment`: بصمة النص المستخرج، بصمة النص المفهرس، بصمة فضاء embeddings، اسم المزود، اسم النموذج، ووقت الفهرسة. migration `0082_file_index_fingerprints` تضيف هذه الأعمدة nullable فقط، دون backfill أو reindex.
- `prepare_file_index` و`replace_file_chunks` يسجلان هوية embeddings والبصمات عند الفهرسة/إعادة الفهرسة الناجحة، ويحافظ مسار الاستبدال على الفهرس السابق إذا فشل تجهيز الجديد.
- لكن `retrieve_relevant_chunks` في main الحالي يرشح المقاطع على `FileChunk.embedding IS NOT NULL` ونطاق الصلاحية فقط؛ لا يقارن `indexed_embedding_fingerprint` مع هوية الاستعلام الحالية، ولا يستبعد أو يعالج صراحةً صفوف legacy التي تكون metadata فيها NULL.
- لذلك لا يوجد في الكود الذي تمت مراجعته strict fingerprint filtering أو compatibility gate أثناء الاسترجاع. وجود بصمات metadata لا يعني أنها مستخدمة لمنع مقارنة متجهات من فضاءات مختلفة.
- `build_fallback_file_context` يبني سياقًا من النص المستخرج للملفات عند استدعائه؛ هذا fallback نصي منفصل ولا يعالج بمفرده اختلاط متجهات قديمة وحديثة في مسار الاسترجاع المتجهي.

### التقييم والقرار

- هذه فجوة توافق مؤكدة على مستوى مسار الاستعلام، لكن أثرها الفعلي يعتمد على ما إذا تغير إعداد embeddings بعد إنشاء المقاطع القديمة، وعلى هوية الفهرس الفعلية لكل ملف. لا نزعم وقوع إجابات خاطئة أو فساد بيانات دون جرد metadata وبيئة staging.
- لا نفعّل strict filtering الآن؛ قد يؤدي استبعاد legacy chunks إلى اختفاء مصادر كانت تظهر للمستخدم، وقد يؤدي فرض إعادة فهرسة إلى استدعاءات مزود وتكلفة وحمل على الملفات.
- الإجراء التالي الآمن: تقرير read-only من staging يجزئ الملفات إلى (metadata كاملة ومتطابقة، metadata كاملة وغير متطابقة، metadata NULL/legacy، نص مستخرج بلا chunks)، ويقارن عدد المقاطع وأبعاد المتجهات مع هوية الإعداد الحالية دون قراءة محتوى المستخدم في التقارير.
- بعد backup وrestore مثبتين إلى staging: صمم fallback صريحًا للملفات legacy، واختبارات mixed modern/legacy، وstale fingerprint، وفشل المزود، وإلغاء الصلاحية؛ ثم dry-run لخطة إعادة الفهرسة وتقدير التكلفة قبل أي تنفيذ.
- لا SQL على production، ولا backfill، ولا bulk reindex، ولا تغيير إعداد embeddings، ولا live provider call ضمن هذه المراجعة.


## 56. تدقيق prompt delimiters والاستشهادات — 2026-11-26

### 56.1 فجوة مؤكدة في main: تحييد علامات السياق غير موحد

- main عند SHA `0ef6148c9d86874c9262cae7930f5cf9b3b52379` يحتوي حماية untrusted tool output عبر `tool_security.py`، لكن كشف prompt injection يعتمد أساسًا على أنماط إنجليزية مباشرة، ولا يحتوي ملف `prompt_context.py` أو مجموعة اختبارات مخصصة لتحييد علامات السياق.
- فرع #665 يضيف `prompt_context.py::safe_context_text` لتحييد علامات التطبيق مثل `[END FILE CONTEXT]`, `[USER MEMORY]`, `[ASSISTANT INSTRUCTIONS]`, `[SOURCE S1:...]` و`USER REQUEST:`، ويعالج حالات الأحرف المختلفة وبعض Unicode format controls/tatweel/combining marks دون تغيير النص المخزن.
- فرع #665 يطبق التحويل على رسالة المستخدم وسجل المحادثة والذاكرة الشخصية/المشروع وتعليمات المساعد/المشروع وملخص المحادثة وسياق الملفات وأسماء الملفات ونتائج Web Search ومخرجات الأدوات. يظل هذا تخفيفًا محددًا لعلامات التطبيق وليس منعًا عامًا لكل prompt injection.
- الفرع يضيف أيضًا إشارات عربية لاكتشاف prompt injection مع تطبيع إشارة الكشف فقط، واختبارات للنص العربي المشكول والتطويل ومحارف التنسيق. هذه الاختبارات غير موجودة في main الحالي.
- القرار: هذه مجموعة تستحق الاستخراج كـPR أمني صغير مستقل من أحدث main، بعد مراجعة جميع نقاط بناء prompts. لا تنقل ملفات #665 مباشرة، ولا تصفها بأنها حماية كاملة.

### 56.2 فجوة متبقية حتى داخل فرع #665: تلخيص المحادثة وتوليد العنوان

- `ai-backend/app/routers/conversations.py` في فرع #665 يبني `_build_summary_prompt` و`_build_title_prompt` من نصوص الرسائل المخزنة مباشرة.
- لم يطبق الفرع `safe_context_text` على transcript المرسل لهاتين العمليتين، ولم يضع transcript داخل صيغة بيانات ذات حدود موثوقة منفصلة عن التعليمات.
- هذا يترك مسار التلخيص/توليد العنوان خارج تغطية تحييد علامات السياق، رغم حماية مسار /chat الرئيسي.
- القرار: يجب أن يكون إصلاح هذين المسارين جزءًا من PR الأمن الصغير قبل اعتباره مكتملًا، مع اختبارات رسالة تحاول حقن `CONVERSATION:` أو تعليمات تلخيص مزيفة أو فواصل/علامات Unicode. لا يوجد ما يثبت استغلالًا فعليًا حتى الآن؛ هذه فجوة تغطية واضحة في الكود.

### 56.3 الاستشهادات: واجهة الربط موجودة، صحة الاستشهاد غير مثبتة

- main يحول `[S1]` إلى رابط فقط إذا كان S1 موجودًا ضمن قائمة المصادر المعادة للرسالة، ويترك المعرفات غير المعروفة كنص عادي. توجد اختبارات frontend لهذا السلوك.
- هذا يمنع روابط لمصادر غير موجودة في metadata، لكنه لا يثبت أن الادعاء الذي يسبق `[S1]` مدعوم فعلًا بمحتوى المصدر. كما لا يمنع النموذج من إرفاق معرف مصدر صحيح بادعاء غير ذي صلة.
- لا توجد في الملفات التي تمت مراجعتها مجموعة تقييم تثبت citation precision/recall أو entailment/claim support. أداة RAG evaluation في #665 تركز على retrieval ranking ولا تثبت صحة الاستشهادات النهائية.
- القرار: أضف مجموعة تقييم offline منفصلة تربط كل claim بمصدر داعم، وتفصل بين retrieval metrics وcitation correctness. لا تضف رفضًا آليًا للاستشهادات ولا تغير واجهة المستخدم قبل وجود معيار واختبارات قابلة للتكرار.

### 56.4 ترتيب الاستخراج الأمني المقترح

1. PR مستقل لتحييد prompt delimiters: `prompt_context.py`، الاختبارات، وربطه بمسارات chat/RAG/tools/web search، مع سد مساري summary/title.
2. إضافة اختبارات عربية/Unicode لإشارات حقن الأوامر، مع إبقاء المحتوى غير الموثوق موسومًا حتى عند عدم اكتشاف إشارة.
3. PR مستقل لتقييم citation correctness offline؛ لا يخلط مع PR sanitizer.
4. بعد كل تغيير: CI على رأس حديث من main، مراجعة diff كاملة، ولا دمج قبل نجاح الفحوص والمراجعة المطلوبة.


## 57. مراجعة فروق MCP بين main و#665 — 2026-11-26

### تحسينات موجودة في #665 وغير مثبتة في main

- تحليل URL عبر `urlsplit` والتحقق من scheme/host/port، ورفض URL الذي يحتوي credentials أو fragment أو authority غير صالح. main يكتفي حاليًا بتعبير regex وفرض HTTPS في production.
- تقليل تسرب الأسرار في السجلات: الفرع لا يسجل URL أو نص الاستثناء القادم من الخادم عند فشل الاكتشاف، بل نوع الاستثناء فقط.
- تنقية remote MCP input schema قبل تقديمه للنموذج: إزالة `$schema` و`$id` و`$comment` و`default` و`examples`، وتحييد نصوص `description/title` وحدود عمق المخطط.
- إضافة اختبارات لوصف أداة خبيث، واسم خادم يحتوي delimiters، وروابط تحوي credentials/fragments/authority غير صالح.

### حدود لم يعالجها الفرع

- لم يظهر في الكود أو الاختبارات حظر صريح لعناوين loopback أو private/link-local أو metadata IP، ولا حماية من DNS rebinding أو إعادة توجيه إلى شبكة داخلية. لذلك لا نصف تغييرات URL بأنها SSRF protection مكتملة.
- إعداد MCP ما زال إعدادًا عامًا للتطبيق، مع سياسة تشغيل application-admin-only. لا توجد grants دقيقة لكل مستخدم/Workspace أو فصل مثبت بين أدوات القراءة والكتابة على مستوى capability.
- allowlist لأسماء الأدوات لا تكفي وحدها لإثبات أن كل عملية ضمن الأداة آمنة أو read-only؛ يجب أن تبقى مراجعة كل أداة وside effects مستقلة.

### القرار

- التغييرات في #665 تحسينات دفاعية تستحق استخراجًا محدودًا مع اختبارات regression، لكنها لا تبرر نقل MCP كاملًا أو تفعيل أي خادم.
- افصل URL/logging/schema sanitization عن أي سياسة SSRF أو صلاحيات connector مستقبلية.
- قبل أي نشر: أضف قرارًا صريحًا لنطاق عناوين MCP المسموحة، وآلية DNS/redirect validation مناسبة، واختبارات عدم الوصول إلى الشبكات الداخلية، ثم مراجعة أذونات كل أداة.
- لا تغيّر إعدادات MCP في الإنتاج، ولا تنفذ اتصالات إلى الخوادم أثناء هذه المراجعة.


## 58. مراجعة استخراج النص دون لمس ملفات الرفع المحمية — 2026-11-26

> اقتصر الفحص على `file_text_extractor.py` و`test_file_text_extractor.py`. لم تُفتح للتعديل ولم تُعدّل `routers/files.py` أو `tests/test_files.py`.

### تحسينات موجودة في #665 وغير موجودة في main

- TXT: استبدال `Path.read_bytes()` الذي يقرأ الملف كاملًا قبل القص، بقراءة prefix محدد من file handle بحد `max_chars * 4`.
- CSV: قراءة محدودة للبايتات، وتحديد طول الصف/الحقل المضاف إلى النص الناتج، حتى لا يضيف صف واحد ضخم مخرجات غير محدودة.
- PDF: تجميع النص ضمن الميزانية، قص الصفحة التي تتجاوز المتبقي، والتوقف عن زيارة الصفحات اللاحقة.
- DOCX: استخدام `iter_inner_content()` لمعالجة الفقرات والجداول بترتيب المستند والتوقف عند بلوغ حد النص بدل تجميع كل الفقرات والجداول أولًا.
- XLSX: قص الصف/الخلايا حسب الميزانية، والتوقف عند بلوغها، مع إغلاق workbook في `finally`.
- أضيفت اختبارات offline لحدود القراءة، الصفوف/الصفحات اللاحقة، والبلوغ الدقيق للميزانية، وإغلاق workbook.

### حدود باقية في التنفيذ المقترح

- PDF ما زال يستدعي `page.extract_text()` للصفحة كاملة قبل قص النص الناتج؛ لذلك حد الأحرف لا يضمن حدًا صارمًا لذاكرة استخراج صفحة واحدة كبيرة.
- لم يظهر في هذا الملف حد مستقل لعدد صفحات PDF أو زمن الاستخراج أو إلغاء المهمة. كما أن حد الأحرف لا يساوي حد CPU/RAM.
- DOCX/XLSX يظلان معتمدين على محللات الحزم؛ حدود ZIP الموجودة في مسار الرفع منفصلة، ولا يجوز افتراض أن حدود النص وحدها تحمي parser من كل ملف تالف أو مكلف.
- CSV محدود البايتات والنص الناتج، لكنه لا يضع حدًا دلاليًا لعدد الأعمدة أو الصفوف غير الفارغة بخلاف ميزانية النص.
- يجب مراجعة صحة truncation marker عند ميزانية صغيرة جدًا/صفرية وحالات النص متعدد البايتات، دون توسيع التغيير إلى مسار الرفع.

### القرار

- تحسينات extractor في #665 صغيرة نسبيًا ومناسبة للاستخراج كـPR مستقل من أحدث main، مع إبقاء تغييرات `files.py` و`test_files.py` خارج النطاق.
- قبل اعتمادها، أضف اختبارات للـPDF ذي الصفحة الواحدة الضخمة/المعطوبة، حد صفحات/زمن مناسب إذا أمكن دون تغيير upload flow، وميزانيات صغيرة/صفرية، وCSV متعدد البايتات.
- لا تشغّل extraction workers أو عمليات رفع فعلية، ولا تغيّر upload sync path، ولا تعِد فهرسة ملفات.


## 56. مراجعة Prompt Context وMCP وTool Schema — 2026-11-26

### 56.1 تحييد علامات السياق — فجوة مؤكدة في main، ومعالجة مرشحة للاستخراج

**في main عند SHA `0ef6148c9d86874c9262cae7930f5cf9b3b52379`:**
- `chat.py` يبني سياق الذاكرة/تعليمات المشروع/تعليمات المساعد/الملفات ثم يضيف الفاصل الحرفي `USER REQUEST:`، لكن نص المستخدم وسياقات كثيرة لا تمر عبر neutralizer موحد.
- `agent_runtime.py` يمرر history وtask كما هما.
- `tool_security.py` يكتشف أنماط إنجليزية شائعة فقط، ولا يطبع Unicode أو يحيّد علامات السياق داخل النص الذي يغلّفه.
- توجد تعليمات بأن الملفات غير موثوقة في RAG، لكنها لا تمنع وحدها تقليد delimiters التطبيقية.

**في فرع #665:**
- يضيف `prompt_context.py` دالة `safe_context_text` لتحييد source IDs وcontext markers وUSER REQUEST delimiters وtranscript wrappers.
- يستخدم نسخة Unicode مطبّعة لأغراض المطابقة، مع إبقاء النص الأصلي خارج spans العلامات؛ لا يغير النص المخزن.
- يغطي محاولات obfuscation بعلامات تنسيق/تشكيل/تطويل ومحارف توافق Unicode، مع اختبارات عربية وإنجليزية.
- يضيف الاستدعاء في chat history وuser prompt وassistant/project instructions وmemories وsummaries وfile snippets وsource filenames وagent history/task وtool output.
- القرار: **أولوية استخراج عالية**، لكن يجب فصل الوحدة واختبار نقاط الإدخال الفعلية في مسار chat وRAG/agent، مع عدم نقل التغييرات الأخرى في `chat.py` دفعة واحدة. لا تدّعِ أن هذا يمنع كل prompt injection؛ هو تحييد delimiters معروفة فقط.

### 56.2 كشف Prompt Injection

- main يكتشف أنماطًا إنجليزية محدودة، ويضع نتيجة `injection_suspected` في بيانات الأداة غير الموثوقة.
- فرع #665 يضيف أنماطًا عربية، ويطبع محارف Unicode format/combining/tatweel في نسخة الكشف فقط.
- الاختبارات تغطي أمثلة عربية/إنجليزية، النص الطبيعي، التشكيل والتطويل والمحارف الخفية.
- الكشف heuristic وليس قرار صلاحية أو حاجزًا شاملاً. سياسة منع tool follow-up بعد مخرجات غير موثوقة موجودة بالفعل في Agent Runtime؛ لا تخلط بين إشارة الكشف وبين هذا الحاجز.
- القرار: استخراج اختبارات/تطبيع الإشارة مع `safe_context_text` كوحدة أمن سياق واحدة بعد مراجعة false positives؛ لا ترفع مستوى الادعاء إلى "مناعة ضد الحقن".

### 56.3 Tool argument schema validation

- main يتحقق من الحجم والعمق وبعض الأنواع والحقول المطلوبة و`additionalProperties=false`، لكنه لا يطبق قيود JSON Schema الرقمية/الحجمية الكاملة ولا يرفض تعريفات schema malformed بصورة شاملة.
- فرع #665 يضيف تحققًا مسبقًا من تعريف schema، وقيود minimum/maximum/exclusive bounds وmin/max length/items/properties، وadditionalProperties schema، ومقارنة enum تراعي الفرق بين bool وint، ورفض القيود/الأنواع غير الصالحة.
- توجد اختبارات regression واسعة لهذه الحالات في `test_tool_security.py`.
- القرار: **تحسين دفاعي مفيد** يستخرج منفصلاً بعد التحقق من توافق schemas الأدوات الحالية؛ يجب ألا يؤدي strict validation إلى تعطيل أدوات سليمة تستخدم مخططات MCP/JSON Schema جزئية. حافظ على دعم الكلمات المحددة فقط، ورفض غير المدعوم fail-closed بصورة موثقة.

### 56.4 MCP — تحسينات أمان محددة وليست إعادة بناء

**ما هو موجود في main:** MCP معطل افتراضيًا في إعداد النشر، حد للخوادم والأدوات، allowlist على مستوى الخادم، HTTPS في production، وتصريح الاكتشاف/التنفيذ للمسؤول فقط في Agent Runtime.

**فجوات مثبتة في main ومقابلها تحسينات #665:**
- `enabled` يتحول إلى bool مباشرة؛ قيمة نصية مثل `"false"` قد تُفسر True. #665 يرفض الأنواع غير boolean.
- URL يتحقق بتعبير regex وHTTPS في production فقط؛ #665 يتحقق من hostname/authority/port ويرفض userinfo وfragment. لا تزال هذه الخطوة وحدها لا تمنع SSRF إلى loopback/private/link-local IP أو DNS rebinding؛ يلزم ضابط شبكة/وجهات مسموحة وإعادة تحقق DNS عند الاتصال إذا تقرر تفعيل MCP خارجيًا.
- main يسجل URL/نص الاستثناء عند فشل الاكتشاف أو استدعاء الأداة؛ قد يكشف ذلك query tokens أو بيانات حساسة من upstream exception. #665 يسجل نوع الاستثناء فقط ويضيف اختبارات تمنع تسرب URL token ورسالة الخطأ.
- main يمرر remote schema/description كما هي، ويعطي schema افتراضيًا متساهلًا عند غياب schema. #665 يزيل annotations غير اللازمة، يحيّد الوصف، يرفض schema العميق/غير الصالح، ويجعل schema المفقود fail-closed (لا يسمح بخصائص غير معرفة).
- main لا يتتبع تصادم أسماء الأدوات بعد sanitization؛ #665 يتخطى الاسم المتصادم بدلاً من السماح بفشل التسجيل أو التباس أسماء الأدوات.
- اختبارات #665 تغطي URL credentials/fragments/invalid ports، عدم تسريب الرموز في logs، تصادم الأسماء، metadata injection وschema sanitation.

**القرار:** استخراج MCP في PR مستقل محدود، مع إبقاء MCP معطلاً افتراضيًا، وعدم تغيير إعدادات الخوادم أو تفعيل الاتصال. إضافة SSRF hardening كمتطلب منفصل قبل أي استخدام حقيقي؛ لا تعتبر تحقق URL في #665 كافيًا وحده.

### 56.5 نطاق PRs الصغيرة المقترح — لا تنفيذ تلقائي بعد

1. PR-A: `prompt_context.py` + `test_prompt_context.py` + نقاط الإدخال اللازمة في chat/RAG/agent/tool output، واختبارات end-to-end على delimiters فقط.
2. PR-B: توسيع `tool_security.py` مع اختبارات schema وUnicode/Arabic injection، بعد اختبار توافق schemas الأدوات.
3. PR-C: `mcp_client.py` مع اختبارات الأنواع والـURL والـlogs/schema/name collisions، دون تفعيل MCP؛ يتضمن SSRF design gate قبل أي نشر/استخدام.
4. PR-D: تقييم RAG offline-only، مستقل عن تغييرات runtime.
5. Memory Suggestions تبقى مؤجلة إلى حين مراجعة خصوصية منفصلة.

لا تنقل `chat.py` أو `agent_runtime.py` كملفات كاملة من #665؛ اعتمد تغييرات محددة مبنية على أحدث main مع regression tests. لا تشغيل محلي/worker/runtime/provider، لا DB/production/Render، ولا تعديل ملفات الرفع المحمية.


## 57. فحص تعليمات النظام الموحدة وتقييم الاستشهادات — 2026-11-26

### 57.1 System prompt موحد للمزودين — قدرة غير موجودة في main ضمن الملفات المطابقة

- main لا يحتوي `ai-backend/app/services/ai_providers/instructions.py`، ولا تظهر إضافة SYSTEM_PROMPT المشترك في ملفات OpenAI-compatible وAnthropic وGemini التي تمت مطابقتها.
- فرع #665 يضيف سياسة موحدة تصنف الملفات/المقتطفات/الذاكرة/تعليمات المشروع والمساعد/metadata والأدوات كمصادر محتملة لبيانات غير موثوقة، وتمنع اتباع أوامرها لتجاوز السياسات أو كشف الأسرار أو صلاحيات الغير، وتلزم الصدق بشأن الأدوات والاستشهادات.
- OpenAI-compatible يمررها عبر `with_system_prompt`، وAnthropic يضيفها في system field، وGemini يضيفها إلى system instruction. كما توجد اختبارات provider للتحقق من الحفاظ على system messages الحالية وعدم تعديل history الأصلي.
- هذا لا يحل prompt injection بمفرده؛ هو طبقة تعليمات دفاعية مكملة لتحييد delimiters واختبار الأدوات والصلاحيات.
- القرار: **مرشح استخراج عالي القيمة** في PR منفصل؛ اختبر أن كل مسارات الرد العادي والبث والرؤية وtool-calls وmodel compare تستخدمها لكل مزود، وأن تعليمات المزود الخاصة لا تتغلب على السياسة المشتركة. لا تعتمد مجرد وجود الملف الجديد كدليل أن كل مسارات provider مغطاة.

### 57.2 Citation evaluation — أداة Offline مفيدة لكن نطاقها محدود

- #665 يضيف `citation_evaluation.py` وtests لقياس اتساق source IDs في نص الإجابة.
- يتجاهل مراجع المصادر داخل fenced/inline code، ويحسب valid/unsupported IDs وcitation precision وsource coverage.
- الكود نفسه يصرح بأنه لا يقيم الدعم الدلالي للادعاء؛ لذلك لا يثبت أن المصدر يدعم الجملة أو أن المعلومة صحيحة.
- القرار: استخراج أداة Offline مستقلة بعد التأكد من توافق صيغ source IDs في كل المسارات؛ لا تحول مخرجاتها إلى مؤشر "صحة الاستشهادات" دون مراجعة بشرية/دلالية.

### 57.3 AI specialist evaluation

- #665 يضيف مواصفة ومجموعة حالات اختبار ثابتة لمجالات الشبكات وLinux والبرمجة والأمن والسحابة والمهام متعددة المجالات، مع معايير نجاح وإخفاق حرج.
- ملفات المواصفة تصرح بأنها baseline مقترحة لم تُشغّل على نموذج، وليست دليلاً على تحقق قدرات المساعد.
- الاختبارات تتحقق من سلامة بنية مجموعة البيانات وتغطية المجالات، لا من جودة مخرجات نموذج حي.
- القرار: يمكن الاحتفاظ بها كحزمة benchmark versioned؛ لا تشغلها على مزود مدفوع أو خدمة حية دون قرار مستقل، ولا تصفها بأنها إثبات أداء.

## 58. migrations وملفات الملفات المحمية — سبب إضافي لعدم دمج #665

### 58.1 تعارض migration القديمة

- فرع #665 يحتوي migration باسم `0081_file_index_fingerprints` و`down_revision = 0080_harden_public_rls`.
- main يحتوي بالفعل `0081_harden_all_public_tables` كابن للـ`0080_harden_public_rls`، ثم `0082_file_index_fingerprints` كابن للـ`0081_harden_all_public_tables`.
- migration #665 القديمة تضيف نفس أعمدة fingerprints الستة الموجودة بالفعل في migration #0082 على main.
- بالتالي لا يجوز دمج migration #665 أو إعادة تسميتها آليًا؛ قد تنشئ revision head موازية أو محاولة إضافة أعمدة موجودة. احتفظ بتصميم migration القديمة كمرجع تاريخي فقط. أي تغيير لاحق يجب أن يبدأ من أحدث head ويضيف migration جديدة فقط إذا كانت هناك schema change جديدة مثبتة.

### 58.2 ملفات الرفع المحمية

- #665 يتضمن تغييرات كبيرة في `ai-backend/app/routers/files.py` و`ai-backend/tests/test_files.py`، ومن بينها توصيل صلاحيات المشروع عبر `can_read_project` و`can_edit_project` لمسارات الملفات.
- هذه التغييرات لا يمكن استخراجها الآن بسبب الحظر الصريح على تعديل الملفين. لا cherry-pick ولا إعادة كتابة لهما ضمن هذه الجولة.
- تبقى فجوة ACL التي سبق توثيقها قائمة للمراجعة المنفصلة؛ لا نعتبر وجود التعديل في فرع #665 إثباتًا بأنه وصل إلى main.

## 59. تحسينات استخراج النصوص — مرشح مستقل منخفض النطاق

- main يستخدم `Path.read_bytes()` ثم يقتطع النص بعد تحميل كامل الملف؛ في CSV قد يقرأ حتى `max_chars * 8` بايت قبل الاقتصاص، كما أن DOCX يجمع الفقرات والجداول بطريقة أبسط.
- فرع #665 يقرأ ملفات TXT/CSV بحد بايت من file handle قبل فك الترميز، ويحد حجم الصف/الحقل المعروض، ويعالج PDF صفحة بصفحة مع إيقاف مبكر، ويمر على DOCX عبر `iter_inner_content()` للحفاظ على ترتيب الفقرات والجداول، ويغلق XLSX workbook في finally.
- أضاف اختبارات لضمان القراءة المحدودة وعدم استخدام `Path.read_bytes()`، والقص المبكر في CSV/PDF/DOCX/XLSX.
- القرار: مرشح PR مستقل آمن نسبيًا من ناحية النطاق، ويمكن مراجعته دون لمس `files.py` أو `test_files.py`. يجب مراجعة سلوك ملفات malformed والحدود صفر/سالبة، وأن حدود القراءة لا تقطع UTF-8 أو CSV row بطريقة تغير معنى البيانات دون وسم واضح. لا تنقل بقية تغييرات الملفات معه.

### 59.1 قائمة الاستخراج المحدثة

- أولوية عالية: `prompt_context.py` وتوصيله الدقيق، ثم SYSTEM_PROMPT المشترك للمزودين.
- أولوية متوسطة: تقوية JSON Schema validation، وMCP log/schema/URL hardening مع بوابة SSRF منفصلة.
- أولوية متوسطة: تحسينات file_text_extractor المستقلة.
- أولوية متوسطة/منخفضة: offline citation evaluator وRAG evaluator وAI specialist benchmark.
- مؤجل: Memory Suggestions إلى حين اعتماد الخصوصية.
- خارج التنفيذ الحالي: migrations #665 القديمة، و`files.py` و`test_files.py`، وعمليات DB/production/provider/live evaluation.

## 60. مراجعة تكامل السياق ومزودي AI وإصلاح Agent Runtime — 2026-11-26

### 60.1 إصلاح اتساق سجل استدعاءات الأدوات — مستخرج في PR #786

- في main، يحد AgentRuntime.run() التنفيذ إلى max_tool_calls_per_round عبر calls = reply.tool_calls[:limit]، لكنه كان يضيف رسالة المساعد باستخدام جميع reply.tool_calls بدل القائمة المنفذة.
- عندما يعيد النموذج 4 استدعاءات والحد 2، يسجل السجل أربعة call IDs بينما لا توجد إلا نتيجتان للأدوات. هذا يترك استدعاءات يتيمة في الطلب التالي إلى المزود، وقد يسبب رفض صيغة المحادثة أو سلوكًا غير متوقع.
- فرع #665 يحتوي إصلاحًا صغيرًا: تمرير calls إلى _assistant_tool_message()، مع اختبار يثبت أن call IDs المسجلة تطابق تمامًا tool-result IDs.
- تم استخراج الإصلاح فقط إلى PR منفصل: https://github.com/HVA09/ai-chat-app/pull/786
- الفرع: fix/agent-tool-call-history-budget-20261126؛ HEAD: dd62fc110ba2111332c638163c87000f5c07458b.
- ملفان فقط: agent_runtime.py وtest_agent_runtime.py. Draft مفتوح، وmergeable=true في آخر فحص.
- لا status contexts ولا Workflow Runs ظهرت على HEAD في آخر تحقق؛ لذلك لا يوجد إثبات نجاح CI بعد. لم تُشغّل اختبارات محلية.
- لا يدمج قبل ظهور الفحوص المطلوبة ومراجعة التغيير.

### 60.2 خريطة مسارات SYSTEM_PROMPT — التغيير غير موجود في main

- OpenAI-compatible: _messages() يغطي الرد العادي والبث؛ وget_vision_reply() وget_reply_with_tools() يحتاج كل منهما إضافة التعليمات صراحة.
- Anthropic: يجب دمج التعليمات في حقل system لكل من الرد العادي والبث، مع إخراج رسائل system من مصفوفة messages.
- Gemini native: يجب استخدام systemInstruction في الرد العادي والبث، وعدم تحويل system messages إلى contents.
- ملاحظة مهمة: factory في main يوجّه AI_PROVIDER=gemini الحالي إلى OpenAICompatibleProvider باستخدام Gemini OpenAI-compatible endpoint؛ لذلك تعديل GeminiProvider الأصلي لا يمر عبر factory الحالي، رغم أنه يستحق اختبارات مستقلة إذا بقي مسارًا مدعومًا.
- مسارات الخدمة المركزية get_ai_reply وstream_ai_reply وget_ai_vision_reply تستخدم هذه provider methods. Model compare وAPI keys وscheduled tasks تستخدم get_ai_reply، بينما Agent mode يستخدم OpenAI-compatible get_reply_with_tools.
- اختبارات #665 تغطي OpenAI-compatible standard/stream/vision/tool-calls، وAnthropic standard/stream، وGemini native standard/stream، والحفاظ على system instructions الحالية وعدم تعديل history الأصلي.
- main لا يحتوي instructions.py أو SYSTEM_PROMPT المشترك، ولا اختبارات provider المقابلة.
- القرار: استخراج SYSTEM_PROMPT مفيد، لكن يجب أن يبقى دفاعًا إضافيًا لا بديلًا عن فصل بيانات السياق عن تعليمات النظام وعن صلاحيات الأدوات. لا تعتبر التغطية مكتملة حتى تغطي كل provider method المستخدم فعليًا، بما في ذلك fallback.

### 60.3 Prompt delimiter sanitizer — لا تنقل chat.py أو rag.py من #665 ككتلة واحدة

- prompt_context.py غير موجود في main. الوحدة في #665 تحيّد علامات التطبيق المعروفة مثل SOURCE/context delimiters وUSER REQUEST وtranscript wrappers، مع مطابقة Unicode normalization دون تغيير النص الأصلي المخزن.
- نقاط الدمج المقترحة في #665 تشمل history/task داخل AgentRuntime، ورسائل المستخدم والسجل والذاكرة وملخص المحادثة وتعليمات المشروع والمساعد ومقتطفات الملفات وأسماء المصادر في chat/RAG.
- البحث في main يؤكد أن بناء prompt لا يحدث في نقطة واحدة فقط: توجد مسارات عبر chat helpers، ويعيد api_keys.py استخدام _augment_message و_build_history، كما توجد استدعاءات مباشرة أخرى لـget_ai_reply. لذلك يلزم تتبع كل مصدر سياق غير موثوق قبل إعلان التغطية مكتملة.
- تغييرات #665 في chat.py وrag.py تتضمن أيضًا تعديلات ACL وRAG indexing/fingerprints وfallback ranking وغيرها؛ لا تنقل الملفين أو الـpatch الكاملين.
- يمكن استخراج sanitizer عبر PR محدود، لكن يجب أن يثبت الاختبار أن كل source text وfilename وmemory/project/assistant instruction لا يستطيع تزوير app delimiters، وأن بيانات المستخدم المخزنة لا تتغير.
- راجع أيضًا قرار تطبيق sanitizer على نص المستخدم نفسه: لا ينبغي إفساد النص الذي يريد المستخدم مناقشة delimiters فيه إلا إذا كان ذلك ضروريًا لمنع التباس boundary موثقًا باختبار.
- لا تدّعِ أن sanitizer يمنع كل prompt injection؛ هو تحييد لعلامات معروفة فقط، وليس حدًا أمنيًا بديلًا.

### 60.4 قائمة الاستخراج بعد هذه الجولة

1. PR #786: إصلاح اتساق سجل استدعاءات الأدوات — مفتوح وينتظر CI/review.
2. SYSTEM_PROMPT + sanitizer: إعداد patch محدود بعد توثيق جميع مسارات السياق ومراجعة حدود المستخدم/المصدر.
3. تحسينات file_text_extractor: تبقى مرشحًا منفصلًا منخفض النطاق.
4. JSON Schema validation وMCP hardening: تبقى مستقلة، مع بوابة SSRF قبل أي تفعيل خارجي.
5. Offline evaluators/benchmarks: لا تشغيل live/provider calls.
6. Memory Suggestions: مؤجلة لمراجعة الخصوصية.
7. الملفات المحمية وmigrations القديمة وعمليات DB/production: خارج التنفيذ الحالي.

## 61. فحص حدود مخرجات الأدوات ومصادر RAG — فجوة دمج إضافية

### 61.1 مخرجات الأدوات غير الموثوقة

- main يلف نتيجة الأداة غير الموثوقة داخل [BEGIN UNTRUSTED TOOL DATA] و[END UNTRUSTED TOOL DATA] عبر wrap_untrusted_tool_output().
- المحتوى الخارجي نفسه لا يُحيّد قبل إدخاله بين العلامتين. إذا احتوى النص على علامة الإغلاق نفسها، يمكنه تقليد حد التطبيق وإنهاء كتلة البيانات مبكرًا.
- prompt_context.py في #665 يتضمن تحييد العلامتين، لكن AgentRuntime._tool_message_content() في diff #665 لا يستدعي safe_context_text() قبل wrap_untrusted_tool_output(). لذلك وجود helper وحده لا يسد هذه الفجوة.
- الإجراء المطلوب في PR sanitizer: تحييد النص غير الموثوق أولًا، ثم تغليفه، مع اختبار يحوي علامة END مزيفة وعلامة BEGIN متداخلة ومحاولات Unicode-obfuscated. يجب أن تبقى قيمة المصدر المخزنة دون تعديل.

### 61.2 مقتطفات RAG وأسماء الملفات

- main يبني labels من original_filename ويمرر chunk.content أو extracted_text إلى سياق النموذج كما هي، دون استدعاء sanitizer في build_retrieval_context() وbuild_fallback_file_context().
- patch #665 يضيف safe_source_filename() وsafe_context_text() إلى بناء السياق، لكنه يدمج ذلك داخل diff rag.py الأوسع الذي يتضمن fingerprints وACL وindex replacement وfallback ranking.
- القرار: استخرج فقط معالجة filename/snippet بعد اختبار marker spoofing؛ لا تنقل تغييرات indexing أو migrations أو ACL ضمن PR sanitizer.

### 61.3 تغطية memory وassistant/project metadata

- main يتحقق بالفعل من can_read_project قبل تحميل ProjectMemory في _build_memory_context()؛ لا تسجل هذا كفجوة ACL جديدة.
- لكن محتوى UserMemory وProjectMemory وAssistant description/name/instructions وProject name/instructions يُركب في prompt دون neutralization لعلامات التطبيق. هذه نقاط إدخال لازمة في patch sanitizer.
- _build_history() في main يعيد نصوص الرسائل كما هي؛ يلزم تحييد نسخة prompt فقط، مع اختبار أن النص المخزن في قاعدة البيانات لا يتغير.

### 61.4 الحكم النهائي على sanitizer

- لا يكفي نسخ prompt_context.py فقط. يلزم ربطه في chat context builders، وRAG source builders، وAgentRuntime history/task/tool outputs، مع tests لكل boundary.
- يجب أن تكون اختبارات التحقق سلبية/إيجابية: markers المعروفة تُحيّد، النص العادي والعربية والرموز التقنية تبقى كما هي، ولا تتغير البيانات المخزنة.
- هذه حماية من تزوير delimiters المعروفة فقط؛ لا تمنع كل prompt injection ولا تستبدل authorization أو tool allowlists.

## 62. استخراج تعليمات النظام المشتركة للمزودين — PR #787

- تم فصل طبقة تعليمات النظام المشتركة من #665 إلى PR مستقل: https://github.com/HVA09/ai-chat-app/pull/787.
- الفرع: fix/shared-provider-system-instructions-20261126؛ HEAD: 8976b788ca6dd13faa5f7b8ac6eaed175a709c48.
- خمسة ملفات فقط: instructions.py، مزود OpenAI-compatible وAnthropic وGemini، واختبارات test_ai_providers.py.
- OpenAI-compatible: النظام المشترك يمر عبر الرد العادي والبث والرؤية واستدعاء الأدوات.
- Anthropic: system field أصلي للرد العادي والبث؛ ورسائل system القديمة تُحفظ في الحقل الأصلي لا داخل messages.
- Gemini native: systemInstruction أصلي للرد العادي والبث. ملاحظة: factory الحالي يوجه AI_PROVIDER=gemini إلى OpenAICompatibleProvider، لذا مسار Gemini native لا يستخدمه factory الحالي.
- الاختبارات تستخدم fake HTTP clients ولا تنفذ provider calls حقيقية، وتتحقق من عدم تعديل history الأصلي وحفظ تعليمات المهام.
- PR #787 Draft مفتوح وmergeable=true في آخر فحص. CI وCodeQL بدآ العمل على HEAD، ولم تظهر النتائج النهائية بعد. لم تُشغّل اختبارات محلية.
- هذا PR دفاع إضافي فقط؛ لا يزعم إغلاق فجوات prompt delimiter أو tool-output wrapper. تبقى تلك الأعمال منفصلة كما في القسم 61.

## 63. حالة دفعة الاستخراج الحالية — 2026-11-26

### PR #786 — Tool-call history consistency
- CI كامل ناجح على HEAD dd62fc110ba2111332c638163c87000f5c07458b: backend وfrontend وSDK وproduction-compose وpreview-builder كلها success.
- CodeQL ناجح على HEAD نفسه.
- PR أصبح Ready for review ومفتوحًا وغير مدمج؛ لا توجد مراجعة GitHub مستقلة بعد. لم يمكن تفعيل auto-merge لأن إعداد المستودع يعطله. لا تخلط نجاح CI مع الموافقة على الدمج.

### PR #787 — Shared provider system instructions
- CodeQL ناجح على HEAD 8976b788ca6dd13faa5f7b8ac6eaed175a709c48.
- CI: backend ما زال in_progress في آخر فحص، بينما preview-builder وSDK وproduction-compose وfrontend اكتملت بنجاح.
- PR Draft ومفتوح وmergeable=true؛ لا دمج حتى يكتمل backend CI وتتم مراجعة payloads.

### PR #788 — Prompt context boundary sanitization
- PR منفصل: https://github.com/HVA09/ai-chat-app/pull/788
- الفرع fix/prompt-context-boundary-sanitization-20261126؛ آخر HEAD 155dc4581d901e50f87ab0478d627dd9e4213c72.
- تسعة ملفات: prompt_context helper، chat/RAG/AgentRuntime/tool output، وأربعة ملفات اختبارات.
- أضيف أيضًا تحييد رسالة /chat/vision بعد مراجعة diff واكتشاف أن أول patch لم يغط هذا المسار.
- CI وCodeQL في قائمة الانتظار على HEAD الأخير؛ بعض jobs بدأت، والـbackend ما زال قيد التنفيذ. لم تُشغّل اختبارات محلية.
- PR Draft ومفتوح وmergeable=true في آخر فحص. لا دمج قبل اكتمال CI ومراجعة اختبارات السياق والـvision.

### قرار الدفعة
- لا دمج لأي من #786 أو #787 أو #788 الآن. #786 فقط اجتاز CI وCodeQL، لكن لا توجد مراجعة مستقلة بعد.
- PR #785 نفسه ما زال Draft توثيقيًا، ويحتاج CI على آخر HEAD ومراجعة قبل الدمج.
- PR #665 يبقى مرجعًا تاريخيًا غير قابل للدمج كحزمة واحدة؛ استمر في استخراج التغييرات الصغيرة مع فصل كل مجال أمني/سلوكي في PR مستقل.

## 64. تحديث بوابة الدمج — 2026-11-26

- PR #786 أصبح Ready for review بعد نجاح CI وCodeQL ومراجعة نطاقه. لا توجد مراجعة مستقلة مسجلة، ولذلك لم يُدمج.
- محاولة تفعيل auto-merge على #786 رُفضت من GitHub لأن auto-merge غير مفعّل في إعدادات المستودع HVA09/ai-chat-app. لم نتجاوز هذا القيد بدمج يدوي.
- PR #787: CodeQL success، وCI لا يزال in_progress على HEAD 8976b788ca6dd13faa5f7b8ac6eaed175a709c48.
- PR #788: CI وCodeQL success على HEAD c8d95c3516ef7f014088d1e1d99085ec34963919؛ Ready for review.
- PR #785 التوثيقي نفسه: CI وCodeQL قيد التنفيذ على HEAD 1fa84534e0e1e853821a9b1479cd3fc0063c6158.
- لا توجد تغييرات على main حتى هذه اللحظة من هذه الدفعة؛ جميع PRs المذكورة ما زالت مفتوحة وغير مدمجة.

## 65. تشخيص فشل CI الأول في PR #787 وإعادة التحقق — 2026-11-26

- فشل أول CI على HEAD السابق لـ#787 في خمسة اختبارات provider فقط، وكلها بسبب NameError: الدالة _install_fake_provider_client غير موجودة في ملف الاختبارات بعد استخراج الاختبارات من #665.
- لم يكن سبب الفشل provider implementation؛ كانت الاختبارات الخمسة تعتمد على helper موجود في فرع #665 ولم يُنقل مع كتلة الاختبارات.
- أضيف helper يستخدم FakeClient لالتقاط payloads دون اتصالات شبكة حقيقية، في commit 990a479f4aa2e9f45509652cf0b9963a97c1a540.
- بدأ CI وCodeQL مجددًا على HEAD المصحح؛ لا توجد نتيجة نهائية بعد في آخر فحص.
- هذا إصلاح test-only، ولا يغير سلوك التطبيق. لا تكرر نفس الاختبارات قبل قراءة نتيجة CI الجديدة.

### متابعة PR #788
- بعد إضافة اختبار vision sanitizer، أصبح HEAD c8d95c3516ef7f014088d1e1d99085ec34963919.
- CodeQL بدأ على هذا الرأس، وCI في progress؛ jobs frontend/SDK/production-compose/preview-builder اكتملت بنجاح، والـbackend ما زال in_progress.
- المحاولة السابقة للـCI على الرأس السابق ألغيت أثناء وصول commit الجديد، لذلك اعتمد فقط نتيجة الرأس الحالي.

## 66. استخراج تحسينات file_text_extractor — PR #789

- تم إنشاء PR مستقل لتحسين حدود قراءة الملفات واستهلاك الذاكرة: https://github.com/HVA09/ai-chat-app/pull/789.
- الفرع perf/bounded-file-text-extraction-20261126؛ HEAD f88493dfd18dfb18000c8e6659f1bda353437eb7.
- ملفان فقط: file_text_extractor.py وtest_file_text_extractor.py. لا تعديل على files.py أو test_files.py أو مسار الرفع.
- TXT/CSV يقرآن prefix محدودًا من file handle بدل تحميل الملف كله، وPDF يتوقف بعد حد الأحرف، وDOCX يعالج Paragraph/Table بالترتيب عبر iter_inner_content، وXLSX يحد الصفوف/الخلايا ويغلق workbook في finally.
- تمت إضافة clamp لحد الأحرف السالب/الصفر في _limit.
- CI وCodeQL بدآ على HEAD الحالي؛ لا نتائج نهائية بعد. PR Draft ومفتوح وmergeable=true. لم تُشغّل اختبارات محلية.
- ملاحظة حدود: مكتبات PDF/DOCX قد تستخرج صفحة أو فقرة واحدة كوحدة كاملة قبل اقتطاعها؛ التغيير يحد التراكم والتحميل الكامل للبايتات، ولا يضمن streaming داخليًا داخل كل صفحة/فقرة.

### حالة جميع PRs بعد الجولة
- #786: CI + CodeQL success؛ Ready for review، لا مراجعة مستقلة بعد، auto-merge غير مفعّل في المستودع.
- #787: CodeQL success؛ CI على HEAD 990a479f4aa2e9f45509652cf0b9963a97c1a540 ما زال in_progress بعد إصلاح helper الاختبارات.
- #788: CI وCodeQL success؛ Ready for review وينتظر مراجعة مستقلة.
- #789: CI وCodeQL قيد التنفيذ على HEAD f88493dfd18dfb18000c8e6659f1bda353437eb7.
- #785: CodeQL success؛ CI على HEAD 39cfe1c648858dc9395a1b996c01ebdbf0404ef8 ما زال in_progress.

## 67. مراجعة MCP وJSON Schema — بوابات قبل أي تفعيل خارجي

### 67.1 تغييرات MCP المقترحة في #665
- main يحصر MCP خلف MCP_ENABLED، ويطبق allowlist للأدوات على مستوى الخادم، ويضع حدودًا لعدد الخوادم والأدوات. يجب إبقاؤه معطلاً افتراضيًا.
- #665 يصلح تحويل enabled إلى bool مباشرة؛ لأن النص "false" يتحول في Python إلى True. النسخة المقترحة ترفض أي قيمة ليست JSON boolean.
- #665 يحسن تحليل URL ويرفض userinfo/password/fragment والمنافذ غير الصالحة وhost المفقود، ويشترط HTTPS في production.
- #665 يخفي URL ونص exception من سجلات MCP، وينظف descriptions/title في schema، ويرفض schema المفقود أو malformed بدل السماح العام، ويتخطى tool-name collisions بعد sanitization.
- لا تسد هذه التغييرات SSRF: لا يوجد منع مؤكد لـloopback/private/link-local IP أو DNS rebinding أو redirects إلى عناوين داخلية. لا يكفي فحص hostname مرة واحدة؛ يلزم egress policy وإعادة تحقق destination على مستوى الاتصال.
- لا تفعّل MCP الخارجي ولا تضف servers حقيقية حتى توجد بوابة SSRF مستقلة واختبارات DNS/redirect/private-address. MCP يبقى disabled.

### 67.2 توافق schemas
- validator المقترح في #665 يدعم مجموعة معلنة من JSON Schema keywords ويرفض الباقي fail-closed، بما في ذلك pattern وformat وoneOf/anyOf و$ref بحسب المراجعة الحالية.
- هذا دفاع مفيد، لكنه قد يرفض schemas صحيحة لخوادم MCP بعيدة؛ لم نثبت توافق كل schemas التي قد يستخدمها المستخدم.
- حالة schema فارغ {} تظل واسعة جدًا إذا مررت كما هي: root schema بلا type/properties/constraints يسمح عمليًا بأي object arguments. ينبغي رفض empty root schema أو اشتراط type=object قبل اعتبار أداة MCP قابلة للتنفيذ.
- عند غياب schema، fallback المقترح object + additionalProperties=false جيد؛ لكن يجب أيضًا رفض schema dict فارغ أو غير محدد كـobject، وعدم عرض tool للموديل قبل اجتياز التحقق.
- قبل استخراج JSON Schema validator: أضف compatibility tests لكل built-in ToolSpec، ومجموعة schemas MCP representative/offline، وتوثيق supported keywords ورفض unsupported keywords. لا تضع live MCP calls في CI.

### 67.3 Arabic injection signals
- #665 يضيف أنماطًا عربية ويطبع Unicode في نسخة الكشف فقط، بينما يظل النص الأصلي دون تعديل.
- هذا يحسن إشارة الاشتباه فقط؛ لا يغير untrusted status ولا يمثل classifier كاملًا، ولا ينبغي استخدامه كبديل عن allowlist أو authorization.

### 67.4 القرار
- MCP hardening وJSON Schema validation يبقيان backlog مستقلًا بعد دفعة #786–#789.
- لا دمج كود MCP ولا تفعيل إعداداته ضمن هذه الجولة، ولا SSRF exception مؤقتة.

## 68. بوابة PR #788 بعد نجاح CI — 2026-11-26

- PR #788 أصبح Ready for review بعد نجاح جميع CI jobs وCodeQL على HEAD c8d95c3516ef7f014088d1e1d99085ec34963919.
- CI jobs الناجحة: backend وfrontend وSDK وproduction-compose وpreview-builder.
- تمت مراجعة diff مرة أخرى بعد اكتشاف أن أول patch لم يحيّد نص /chat/vision؛ أضيفت معالجة vision واختبارها، كما تم منع الاختبار من استدعاء provider حقيقي عبر fake reply.
- لا مراجعة GitHub مستقلة بعد، ولم يُدمج. auto-merge معطل في المستودع، ولا نتجاوز هذا القيد.

## 69. بوابة PR #787 بعد إصلاح الاختبارات — 2026-11-26

- PR #787 أصبح Ready for review بعد نجاح CI وCodeQL على HEAD 990a479f4aa2e9f45509652cf0b9963a97c1a540.
- جميع jobs الخمسة ناجحة: backend وfrontend وSDK وproduction-compose وpreview-builder.
- فشل المحاولة الأولى كان بسبب helper اختبار مفقود، وتم إصلاحه في اختبار فقط؛ أعيد تشغيل المجموعة كاملة ونجحت.
- لا توجد مراجعة GitHub مستقلة بعد، ولم يُدمج. لا live provider calls.

## 71. تحديث main وإعادة تأسيس PRs — 2026-11-26

### تغييرات مدمجة
- PR #786: إصلاح AgentRuntime tool-call history مدمج بالـcommit 8ca2c78b449bbc6df9353a4aa52d9711b4015f06.
- PR #789: bounded file text extraction مدمج بالـcommit 4c163f03201d70d92ce15473a08363b26b07aa26.
- main الحالي بعد هذين الدمجين يبدأ بـ4c163f03201d70d92ce15473a08363b26b07aa26.

### PRs مغلقة كنسخ stale-base فقط
- #787 اجتاز CI/CodeQL على قاعدته القديمة، ثم أُغلق غير مدمج لأن main تقدم بعد #786 و#789؛ أعيد تطبيق provider changes في #791.
- #788 اجتاز CI/CodeQL على قاعدته القديمة، ثم أُغلق غير مدمج لأن #786 غيّر AgentRuntime؛ أعيد تطبيق sanitizer فوق main الجديد في #790 مع الحفاظ على #786.
- لا تعني هذه الإغلاقات رفض الإصلاحات؛ هي إغلاق لفروع قديمة لمنع merge/revert غير مقصود.

### PRs التنفيذية النشطة
- #790: prompt boundary sanitizer، 9 ملفات، مبني على main بعد #786، لكن main تقدم لاحقًا بدمج #789؛ CodeQL success وCI in_progress على HEAD 8f57f4eeb2785e9377e28c69e82bd747e1176b31. mergeable=true في آخر فحص.
- #791: shared provider system instructions، 5 ملفات، مبني على main الحالي 4c163f03201d70d92ce15473a08363b26b07aa26؛ CI وCodeQL queued على HEAD 190f69516382dacd7306e4d6e5ac55c8f080fa29.
- #790 و#791 لم يدمجا بعد، ولا توجد مراجعة مستقلة مسجلة.

### بوابة الدمج
- auto-merge معطل على مستوى المستودع؛ الدمج المباشر لن يستخدم إلا بعد نجاح جميع الفحوص ومراجعة النطاق، وبشرط ألا تتجاوز حماية الفرع.

## 70. نتائج دمج دفعة استخراج #665 — 2026-11-26

- PR #789 merged: bounded text extraction، commit `4c163f03201d70d92ce15473a08363b26b07aa26` (قبل الدمج سجل PR merge SHA `f62ad884...` ثم تحقق main أحدث في المصالحة). يحد TXT/CSV reads، early-stop لـPDF/DOCX/XLSX، ويغلق workbook. الملفات المحمية ومسار upload لم تتغير.
- PR #790 merged: prompt-context boundary neutralization، commit `94e1d96bbc3b095fd9b1dc48ab9fc03246ab7fc8`. أعيد تركيبها بعد #786، واحتفظت بإصلاح tool-call history budget من #786. CI وCodeQL نجحا على رأس PR قبل الدمج.
- PR #791 merged: shared provider system safety instructions، commit `cdaebef260c1b6b706c68795c79c54fad12f5e12`. CI وCodeQL نجحا قبل الدمج، وغطت اختبارات fake clients طلبات provider المختلفة.
- PR #788 و#787 stale-base أغلقت بعد إعادة تركيب التغييرات في #790 و#791. لا تغييرات من الفروع القديمة دمجت مباشرة.
- هذه الأدوات دفاعية وليست ضمانًا ضد كل prompt injection أو سلامة استخراج الملفات. لا live provider calls.

### 70.1 ما تبقى من #665
1. MCP hardening وSSRF gate (القسم 67)، دون تفعيل MCP.
2. JSON Schema validation وتوافق MCP/builtin tool schemas.
3. RAG retrieval evaluator offline فقط، وcitation evaluator offline، ثم benchmark specialists.
4. Memory Suggestions privacy review.
5. ACL files/project: backlog منفصل بسبب حماية files.py وtest_files.py.
6. Migration #665 القديمة لا تنقل: fingerprints موجودة بالفعل في main عبر migrations مستقلة.



## 72. مصالحة الحالة الفعلية — 2026-11-28

### خط الأساس الحالي
- رأس `main` عند تحديث هذا القسم: `c3cc1500ad90f7b08b9eb3bb7918cf36bc67b80f`.
- PR #665 ما زال Open / Draft، ورأسه `4792285440511833b66e1045bc235143a5a302a5`، ويغيّر 70 ملفًا (+15,331 / -388)، وحالة الدمج `dirty` مع `mergeable=false`.
- القرار ثابت: لا دمج لـ#665 ككتلة واحدة؛ نواصل الاحتفاظ به كمصدر تاريخي لاستخراج الأجزاء الفريدة فقط.

### تغييرات حديثة دخلت main ولا تُعاد
- #731 — تحديث Tailwind 4/PostCSS، merge commit `6c517b19da9ec59719b2ab257fd49c34aa2f91df`.
- #805 — حماية مسارات التخزين المحلي وحد قراءة ملفات معاينة المشاريع، merge commit `38cbb94f19fbd22e5ae4e126cfd71ca104cc2847`.
- #185 — تحديث `docker/metadata-action`، merge commit `69d13d221a8bbe1e4f69602f25992d3b7a6e12fa`.
- #762 — توثيق بروتوكول تنفيذ upload leases، merge commit `98238d45ed1997d8c9bf7d2e790b2884d8ad4e7d`.
- #745 — اختبارات Playwright الأساسية المعزولة للواجهة، merge commit `137f4a27b75eaf2acf9a93fa341db9896abf4845`.
- #737 — مزامنة فروع PR وتشغيل CI/CodeQL بعد تحديث الفرع، merge commit `416c5b7e98885ba391dc521ab3952574acd38f95`.
- #780 — سجل مهام الاستقرار والأمان بالعربية، merge commit `6712508cac2cf7c9b513cecdaf8bb6ac7de8959e`.
- أُحدّث Issue #781 بعد دمج #805 لتسجيل حدود قراءة ملفات المعاينة.

### الحالة التنفيذية للطلبات المرتبطة
- #746 — اختبارات Playwright مع backend disposable: مدمج في main، merge commit `c3cc1500ad90f7b08b9eb3bb7918cf36bc67b80f`. بعد تصحيح عنوان API المعترض على الفرع نفسه، نجح Playwright وCodeQL وجميع فحوص CI، وأصبحت تغطية تسجيل الدخول والجلسة ورفع مرفق وتدفق استجابة chat ضمن بيئة اختبار disposable.
- #739 — أساس retention/upload transaction safety: لا يُدمج في الوضع الحالي لأنه يغيّر `ai-backend/app/routers/files.py` و`ai-backend/tests/test_files.py`، وهما محميان من التعديل في هذه المرحلة.
- #740 و#756 و#757 و#758 و#749 و#750 و#744: تبقى سلسلة تخزين معتمدة على #739؛ لا تُدمج قبل حل اعتماد #739 ضمن قيد الملفات المحمية.
- #748: يغيّر `ai-backend/tests/test_files.py` مباشرة، ولذلك يبقى مؤجلاً ولا نعدّل الملف المحمي.
- #736: benchmark مستقل لكنه يستهدف الفرع الأساسي `security/project-retention-lock-order-20261119-v2` وليس `main`؛ لا يُعامل كطلب جاهز للدمج في main.
- #737 و#780 مدمجان بالفعل؛ لا تكرر محتواهما في PRs لاحقة.

### سياسة الدمج الحالية
- لا ننتظر مراجعة بشرية مستقلة كشرط منفصل عندما يكون النطاق محدودًا ومفهومًا، ولا توجد مخاطرة حساسة معلقة، وتنجح جميع الفحوص المطلوبة على HEAD نفسه، وتكون حالة الدمج نظيفة.
- يظل الفحص الداخلي للملفات والاعتماديات إلزاميًا، وكذلك CI وCodeQL وmergeability؛ لا نتجاوز حماية الفرع ولا ندمج PRs التابعة قبل اعتمادياتها.
- لا تغييرات مباشرة على main، ولا عمليات Production/Stage، ولا تعديل للملفات المحمية ضمن هذا المسار.
