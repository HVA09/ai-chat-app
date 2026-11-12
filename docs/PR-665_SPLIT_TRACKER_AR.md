# سجل تفكيك PR #665 — مرجع التنفيذ

**آخر تحديث:** 2026-11-12 (Africa/Tripoli)  
**الحالة:** سجل عمل مفتوح — PR #665 ما زال Draft وغير قابل للدمج بصورته الحالية.  
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

