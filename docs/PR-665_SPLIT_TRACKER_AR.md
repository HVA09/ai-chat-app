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
