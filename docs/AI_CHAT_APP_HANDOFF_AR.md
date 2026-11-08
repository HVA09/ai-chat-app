# سجل الاستمرار — AI Chat App
تاريخ اللقطة: 2026-11-08  
المستودع: `HVA09/ai-chat-app`  
المصدر الدائم لهذه المتابعة: هذا الملف مع تقرير `docs/STABILITY_AUDIT_AR_2026-11-08.md`.

> **تنبيه استمرارية:** يُستخدم هذا السجل لاستعادة سياق العمل عند انقطاع المحادثة أو بدء محادثة جديدة. يجب إعادة قراءة حالة GitHub والفحوص قبل أي إجراء؛ قد تتغير الفروع والنتائج بعد تاريخ هذه اللقطة.

## 1. نطاق المشروع والقرارات الثابتة

- هذا السجل يخص **AI Chat App فقط**. لا تخلطه مع النظام التعليمي المستقل أو منصة Lumen أو أي مشروع آخر.
- المجال التعليمي داخل AI Chat App هو قدرة مستقبلية للمساعد التقني على تعليم الشبكات وLinux والبرمجة والأمن السيبراني والسحابة؛ وليس مشروع منصة تعليمية مستقلة.
- القرار الهندسي الساري: **تجميد الميزات الجديدة مؤقتًا، وتثبيت الأساس، وإغلاق بوابات المرحلة H قبل التوسع**.
- المطلوب أن تكون التغييرات قابلة للمراجعة والاختبار والرجوع، وأن تُوثّق الحالة مع SHA وروابط الفحوص، لا بالاعتماد على مربعات Markdown فقط.
- الأولوية للحلول المجانية؛ لا تضف موارد أو خدمات مدفوعة.
- لا تغيّر الإنتاج أو Render أو Supabase أو الأسرار أو قاعدة البيانات، ولا تنفذ إعادة فهرسة جماعية أو اختبار مزوّد حي يستهلك الحصة، دون طلب وموافقة صريحة مستقلين.
- لا تدمج PR أو تنشر إصدارًا لمجرد نجاح CI. النجاح شرط ضروري وليس قبولًا إنتاجيًا.
- اتصال المستخدم بالإنترنت قد ينقطع؛ لذلك يجب تحديث هذا الملف عند كل محطة ذات معنى، مع إبقاء رابط PR المرجعي.

## 2. آخر حالة موثقة لـ main

- الفرع: `main`
- SHA عند التدقيق: `b690c149610a704f78d7f4ee9e6f377be7466703`
- لم يُجرِ هذا التدقيق أي تعديل على `main` أو الإنتاج.
- لا يُفترض أن SHA ما زال الأحدث؛ أعد قراءته قبل تنفيذ أي عمل.

### أدلة تشغيل الإنتاج التي نجحت في 2026-11-08

| التحقق | Run | النتيجة | ما يثبته وما لا يثبته |
|---|---:|---|---|
| Production Smoke | [42471250466](https://github.com/HVA09/ai-chat-app/actions/runs/42471250466) | نجاح | فحص Backend وFrontend و`/health`، وليس رحلة مستخدم كاملة |
| Object Storage Smoke | [42474852932](https://github.com/HVA09/ai-chat-app/actions/runs/42474852932) | نجاح | كتابة وقراءة والتحقق ثم حذف كائن اختبار |
| Production DB Backup | [42467552352](https://github.com/HVA09/ai-chat-app/actions/runs/42467552352) | نجاح | إنشاء نسخة والتحقق من أرشيفها ورفعها والتحقق من وجودها؛ **لا يثبت Restore كاملًا** |

هذه النتائج لا تثبت تسجيل الدخول من Android أو دورة المحادثة أو معالجة الملفات كاملة أو انتهاء أخطاء QueuePool.

## 3. حالة طلبات الدمج المهمة

### PR #664 — تحرير اتصال قاعدة البيانات قبل انتظار SSE

- الرابط: https://github.com/HVA09/ai-chat-app/pull/664
- الحالة وقت اللقطة: Open / Draft / غير مدمج.
- HEAD الفعلي الذي أعادته GitHub: `35ef8e6882e562305e07049d3c1af4b024891ba9`.
- النطاق: 3 ملفات، +374/-1.
- CI على هذا الرأس: [41132462301](https://github.com/HVA09/ai-chat-app/actions/runs/41132462301) — جميع وظائف Backend وFrontend وSDK وPreview Builder وProduction Compose نجحت.
- CodeQL على هذا الرأس: [41132462064](https://github.com/HVA09/ai-chat-app/actions/runs/41132462064) — تحليل Python وJavaScript/TypeScript نجح.
- تنبيه دقة: وصف PR يحتوي SHA أقدم `3dacc04...`؛ اعتمد HEAD الفعلي أعلاه وRuns المرتبطة به، ولا تعتمد على النص القديم في الوصف.
- سبب الأولوية: ظهرت أخطاء `sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 1 reached` في سجلات Render. تعديل SSE واختبارات الانحدار يعالجان مسارًا محددًا، لكن لا يثبتان حل المشكلة في الإنتاج.
- بوابة الإغلاق: تحقق إعداد حماية `main`، وتحقق Render Auto Deploy live، واختبار مرحلي/نشر مضبوط ومراقبة PoolTimeouts و503، ثم اختبارات chat/SSE/regenerate/edit. لا تدمج قبل تحقيق هذه البوابات.

### PR #665 — فصل embeddings وRAG واقتراحات الذاكرة

- الرابط: https://github.com/HVA09/ai-chat-app/pull/665
- الحالة وقت اللقطة: Open / Draft / غير مدمج.
- HEAD الفعلي الذي أعادته GitHub: `4792285440511833b66e1045bc235143a5a302a5`.
- النطاق: 70 ملفًا، +15,331/-388؛ تغيير واسع جدًا ولا يُعامل كوحدة إصدار واحدة.
- CI على هذا الرأس: [41247792816](https://github.com/HVA09/ai-chat-app/actions/runs/41247792816) — جميع وظائف Backend وFrontend وSDK وPreview Builder وProduction Compose نجحت.
- CodeQL على هذا الرأس: [41247792783](https://github.com/HVA09/ai-chat-app/actions/runs/41247792783) — تحليلا Python وJavaScript/TypeScript نجحا.
- تنبيه دقة: وصف PR يشير إلى SHA أقدم `49394a8...`؛ HEAD الفعلي في هذه اللقطة هو SHA أعلاه.
- النطاق يتضمن فصل embeddings، بصمات فهرسة، RAG، fallback، اقتراحات الذاكرة، system prompts، اختبارات وأدوات Benchmark.
- Migration `0081_file_index_fingerprints` تضيف أعمدة nullable؛ الملفات القديمة ذات البصمات NULL لا تدخل semantic retrieval قبل سياسة إعادة فهرسة مناسبة. توجد آلية text fallback محدودة ومقيدة بالصلاحيات.
- benchmark الحالي offline اصطناعي (20 حالة و100 وثيقة و7 مجالات). لا يوجد baseline حي يثبت جودة مزود embeddings أو الإجابات أو الاستشهادات. لا تستخدم `--run-live` دون موافقة منفصلة.
- اقتراحات الذاكرة لا تعني تدريب النموذج: يطلبها المستخدم، يراجع الاقتباس، ويختار الحفظ أو التجاهل. لا يوجد حفظ تلقائي أو fine-tuning تلقائي.
- قرار المراجعة: **لا تدمج الحزمة الكبيرة**. افصلها إلى وحدات PR مستقلة: (أ) embeddings والمخطط وخطة المتجهات القديمة، (ب) صلاحيات الملفات وRAG/fallback، (ج) الذاكرة والخصوصية وتعليمات النظام، (د) benchmark والوثائق. اختبر كل وحدة وخطة الرجوع الخاصة بها.

### PR #671 — تقرير التدقيق والتوثيق

- الرابط: https://github.com/HVA09/ai-chat-app/pull/671
- الفرع: `docs/stability-audit-20261108` إلى `main`.
- الحالة عند آخر فحص: Open / Draft / غير مدمج؛ كان `mergeable=true`.
- HEAD وقت آخر فحص قبل إضافة سجل الاستمرار: `75d28df3de58e51943381f93d1ef1e7da094dfaf`.
- CodeQL: [42481823784](https://github.com/HVA09/ai-chat-app/actions/runs/42481823784) — ناجح.
- CI: [42481823758](https://github.com/HVA09/ai-chat-app/actions/runs/42481823758) — وظائف frontend وSDK وPreview Builder وProduction Compose نجحت؛ وظيفة Backend كانت لا تزال `in_progress` عند آخر قراءة.
- التغيير توثيقي فقط. إضافة هذا السجل إلى الفرع ستغيّر HEAD وتطلق فحوصًا جديدة؛ يجب اعتماد نتائج الفحوص على **الرأس الجديد** بعد إضافته.
- لا تحوّل PR إلى Ready ولا تدمجه حتى تنتهي فحوص الرأس النهائي وتراجع محتوياته.

## 4. بوابات إغلاق H — قائمة التنفيذ المعتمدة

نفّذ بالترتيب، وسجّل لكل بند: الحالة، التاريخ، SHA/PR، دليل الفحص، نتيجة القبول، وخطة الرجوع.

1. **حماية main — غير مفعّلة ومثبتة في قراءة 2026-11-08.** كائن فرع `main` أعاد `protected=false` و`protection.enabled=false`، و`required_status_checks.enforcement_level=off` مع قائمة contexts فارغة. كما أعاد endpoint الخاص بقائمة Rulesets مصفوفة فارغة `[]`. محاولة قراءة تفاصيل Branch Protection أعادت 403 من تكامل GitHub، لكن كائن الفرع نفسه يثبت أن الحماية غير مفعلة. المطلوب من مالك المستودع تفعيل Branch protection أو Ruleset: منع الدفع المباشر، اشتراط PR، اشتراط CI وCodeQL والتحليلات المطلوبة، ومنع الدمج عند فشل الفحوص. لم يتم تغيير أي إعداد.
2. **Render Auto Deploy — يحتاج إعادة تحقق حيّة.** هناك تعارض موثق سابقًا بين إعداد حيّ `autoDeployTrigger=commit` وبين `render.yaml` الذي يحدد `checksPass`. أعد قراءة لوحة Render قبل أي تطبيق. لا تستخدم Apply Blueprint جماعيًا ولا تغيّر إعداد الإنتاج ضمن هذا السجل.
3. **استعادة نسخة قاعدة البيانات — مفتوح.** النسخ والرفع والتحقق من الأرشيف نجح؛ نفّذ Restore فعليًا إلى قاعدة اختبار معزولة، وافحص الجداول والبيانات الأساسية، ووثّق وقت الاستعادة والنتيجة. لا تختبر على قاعدة الإنتاج.
4. **PoolTimeout / SSE — مفتوح حتى التحقق التشغيلي.** راجع PR #664، ثم خطط لاختبار مرحلي ونشر مضبوط بعد تحقق الحماية والنشر. راقب QueuePool timeouts و503 وزمن `/users/me` و`/workspaces` و`/conversations`، واختبر الدردشة والبث والإلغاء وإعادة التوليد والتعديل. لا تعلن الحل اعتمادًا على CI وحده.
5. **قبول Android — مفتوح.** اختبر تسجيل الدخول واستعادة الجلسة، فتح الشريط الجانبي وإغلاقه، التنقل بين المحادثات، إرسال الرسائل، الأزرار والرفع، وتأكد من مواضع زر الإرسال/الإضافة بعد إرفاق ملف. سجّل الجهاز والمتصفح والنتيجة والخطوات الفاشلة.
6. **دورة حياة الملفات — مفتوح.** اختبر upload → storage → read/download → extraction → indexing → retrieval → delete، وكذلك حالات fail/retry، الصلاحيات، عدم فقد البيانات وعدم إنشاء مقاطع مكررة. لا تُجرِ إعادة فهرسة شاملة للملفات القديمة دون خطة وموافقة.
7. **القبول الشامل للمحادثة — مفتوح.** اختبر الرسائل العادية وSSE والإلغاء وإعادة المحاولة والتحرير وإعادة التوليد، وتأكد من عدم تكرار رسائل المستخدم أو فقد حالة المحادثة.

لا تُعتبر H مغلقة حتى تمر البوابات الحرجة أو يُسجل استثناء محدد ومبرر مع مخاطره وموافقة صريحة.

## 5. بعد H — ترتيب العمل

- إغلاق قبول I يدويًا على Android.
- عدم البدء في إعادة هيكلة J أو تحسين الأداء K أو توسيع L قبل استقرار H/I وتحديد خط أساس.
- فصل PR #665 ومراجعة كل وحدة مستقلًا.
- استكمال M/RAG ومراحل المساعد التقني 3–5 بعد توثيق مصدر المعرفة والجودة والاستشهادات.
- لا تبدأ تشغيل الكود والمختبرات والسحابة (N ومراحل المساعد 6–8) قبل اعتماد Sandbox والصلاحيات وحدود الموارد.
- Q (الأمن والخصوصية) وR (الاعتمادية) ضوابط مستمرة على كل المراحل.
- استكمال S ثم قبول T بإصدار محدد ونطاق معلوم.
- Fine-tuning/LoRA اختياري ومتأخر؛ لا يبدأ إلا عند وجود بيانات مرخصة ومنقحة وقياس يثبت الحاجة.
- لا توجد تواريخ إنجاز موثوقة لـ J–T أو المرحلة 11 من خارطة المساعد؛ لا تخترع موعدًا نهائيًا.

## 6. قائمة «لا تفعل»

- لا تخلط AI Chat App مع النظام التعليمي المستقل أو Lumen.
- لا تدمج #664 أو #665 أو #671 تلقائيًا.
- لا تدفع تغييرات مباشرة إلى `main`.
- لا تغيّر بيئة Render/Supabase أو الأسرار أو قاعدة الإنتاج دون إذن منفصل.
- لا تنفذ `--run-live` أو إعادة فهرسة جماعية أو موارد مدفوعة دون موافقة.
- لا تعتبر نجاح smoke أو CI مساويًا لاختبار قبول شامل.
- لا تعتبر نص PR أو قائمة checkboxes أحدث من حالة GitHub الفعلية.

## 7. بروتوكول استئناف العمل عند فتح محادثة جديدة

1. افتح هذا الملف أولًا، ثم `docs/STABILITY_AUDIT_AR_2026-11-08.md`.
2. تحقق من SHA الحالي لـ `main`، وحالة #664 و#665 و#671، ورؤوس الفروع وRuns المرتبطة بكل HEAD.
3. تحقق من الوظائف الفعلية لكل Run، لا من حالة عامة أو وصف PR.
4. حدّث هذا الملف على فرع توثيقي، ثم أعد فحوص PR التوثيقي على أحدث HEAD.
5. أكمل أول بند غير مغلق من قائمة H فقط، مع إبقاء الميزات الجديدة مجمدة.
6. أخبر المستخدم بما تغير فعليًا وما لم يتغير، مع الروابط والأدلة. لا تدّع أن التوثيق في GitHub يضمن بقاء ذاكرة المحادثة نفسها؛ GitHub هو مرجع الاستمرارية الخارجي.

## 8. آخر خطوة تالية

بعد إضافة هذا الملف إلى PR #671: انتظر اكتمال CI/CodeQL على HEAD الجديد؛ راجع الملفين التوثيقيين ونتائج الفحوص؛ اترك PR Draft إن كان أي تحقق ناقصًا. بعد ذلك ابدأ ببوابة حماية `main` وRender Auto Deploy كتحقق/خطة آمنة، دون تعديل الإنتاج، ثم تابع Restore الاختباري وقبول Android ودورة الملفات.


## 9. تحديث متابعة — إعادة تحقق GitHub وRender workspace — 2026-11-08

- تمت إعادة قراءة فرع `main` مباشرة: `protected=false`، و`protection.enabled=false`، و`required_status_checks.enforcement_level=off`، ولا توجد contexts مطلوبة في كائن الفرع.
- endpoint قائمة Rulesets أعاد `[]`. لذلك تعد حماية `main` بندًا مفتوحًا ومثبتًا، وليس مجرد حالة غير معروفة.
- لا توجد أذونات في هذا التدقيق لإجراء تغييرات حماية المستودع؛ لم يتغير أي إعداد في GitHub.
- أظهرت قائمة Render مساحة عمل واحدة باسم `My Workspace`، لكن أداة Render تشترط أن يؤكد المستخدم مساحة العمل قبل قراءة الخدمات. لم يتم اختيار مساحة العمل أو استدعاء خدمات أو قراءة إعدادات Render الحية أو تغييرها.
- الخطوة المطلوبة قبل التحقق الحي من Render: تأكيد أن مساحة العمل المقصودة هي `My Workspace`. بعد التأكيد، تقتصر الخطوة التالية على القراءة والمقارنة فقط؛ لا Blueprint sync ولا تعديل Environment Variables ولا Deploy.


## 10. لقطة متابعة الفحوص والحوكمة — 2026-11-08

### 10.1 PR #671 على الرأس `e632073c389166571fce61b020f1fbd5f0c270c1`

- الحالة وقت هذه اللقطة: Open / Draft / غير مدمج؛ عدد الملفات المتغيرة 2، وكلاهما وثائقي داخل `docs/`.
- CI run [42482405414](https://github.com/HVA09/ai-chat-app/actions/runs/42482405414): `sdk` و`frontend` و`preview-builder` و`production-compose` اكتملت بنجاح؛ `backend` كان لا يزال قيد التنفيذ عند القراءة.
- CodeQL run [42482405280](https://github.com/HVA09/ai-chat-app/actions/runs/42482405280): اكتمل بنجاح لتحليل Python وJavaScript/TypeScript.
- لا توجد مراجعات PR أو review threads مسجلة عند آخر استعلام.
- لا تعتمد على حالة Run قديمة بعد أي commit جديد. يجب قراءة HEAD الحالي وإعادة جلب Runs المرتبطة به، ثم فحص وظائف كل Run.
- بقيت حالة CI غير مكتملة؛ لذلك لا تحول #671 إلى Ready ولا تدمجه عند هذه اللقطة.

### 10.2 نتيجة إعادة فحص حماية main

- قراءة كائن `main` أعادت SHA `b690c149610a704f78d7f4ee9e6f377be7466703`، و`protected=false)، مع تعطيل enforcement لفحوص الحالة وعدم وجود contexts مطلوبة.
- قراءة `/repos/HVA09/ai-chat-app/rulesets` أعادت مصفوفة فارغة `[]`.
- قراءة endpoint التفصيلي `/branches/main/protection` أعادت HTTP 403 من تكامل GitHub؛ لذلك لا تتوفر تفاصيل إضافية من ذلك endpoint، لكن كائن الفرع نفسه يؤكد أن `main` غير محمي في هذه اللقطة.
- بيانات المستودع أظهرت أن صلاحية الحساب المرتبط هي admin، لكن أداة GitHub المتاحة هنا تقصر قراءة branch protection على GET ولا تعرض عملية كتابة لإعداد الحماية. لم يتم إجراء أي تغيير.
- الإجراء المطلوب من مالك المستودع عبر GitHub Settings: إعداد Branch protection أو Ruleset لـ`main`، اشتراط Pull Request، منع force push والحذف والدفع المباشر، اشتراط CI وCodeQL والتحليل الثابت على SHA المحدث، واشتراط تحديث الفرع قبل الدمج. اختبر أن السياسة تظهر فعليًا على `main` بعد حفظها.

### 10.3 قيد Render قبل المتابعة

- ظهر Workspace واحد باسم `My Workspace` في قائمة Render، لكن لا يجوز افتراض أنه مساحة العمل الصحيحة قبل تأكيد المستخدم.
- لم تُقرأ الخدمات أو متغيرات البيئة الحية، ولم تُغيّر أي إعدادات أو تنفذ عمليات Deploy.
- قبل أي قراءة إضافية لخدمات Render: اطلب تأكيدًا صريحًا بأن `My Workspace` هي مساحة العمل المقصودة. بعد التأكيد، ابدأ بقراءة فقط لمطابقة اسم الخدمة والفرع وAuto Deploy والقيم غير السرية ذات الصلة؛ لا تُظهر الأسرار ولا تستخدم Blueprint sync أو Deploy أو تحديث Environment Variables.

### 10.4 الترتيب المباشر عند الاستئناف

1. إعادة التحقق من فحوص PR #671 على أحدث HEAD بعد إضافة هذا التحديث.
2. ترك #671 Draft إذا كان أي فحص لم يكتمل أو ظهر فشل؛ لا دمج توثيقي تلقائيًا.
3. إغلاق حماية `main` من GitHub Settings، ثم إعادة قراءة حالة الفرع للتأكد.
4. طلب تأكيد مساحة Render `My Workspace` قبل قراءة إعدادات الخدمة الحية.
5. بعد تأمين الحماية وفهم Auto Deploy، استكمال Restore إلى قاعدة اختبار، ثم قبول Android ودورة الملفات، دون تغييرات إنتاجية غير معتمدة.


## 11. تحقق Render الحي ونتيجة CI — 2026-11-08

### 11.1 مساحة العمل والخدمات

أكد المستخدم أن مساحة Render الصحيحة هي `My Workspace`، وتم تمرير workspace ID `tea-dagsi5ou01pc73f2g470` صراحةً لكل استعلام. القراءة فقط كشفت:

| الخدمة | النوع | الفرع/الجذر | Auto Deploy | Trigger الحي | ملاحظات |
|---|---|---|---|---|---|
| `ai-chat-backend` | Web / Docker | `main` / `ai-backend` | yes | `commit` | Free، Ohio، health check `/health`، URL `https://ai-chat-backend-ltxa.onrender.com` |
| `ai-chat-frontend` | Static | `main` / `ai-frontend` | yes | `commit` | build `yarn install; yarn build`، publish `dist`، URL `https://ai-chat-frontend-v8ma.onrender.com` |
| `ai-chat-preview-builder` | Web / Docker | `main` / جذر المستودع | yes | `commit` | Free، Ohio، URL `https://ai-chat-preview-builder.onrender.com`؛ خدمة منفصلة لا تظهر في render.yaml الحالي |
| `ai-chat-redis` | Key Value | — | — | — | موجود، status `available`، Free، Ohio، version 8.1.4، persistence off، memory policy allkeys-lru |

توجد كذلك ثلاث خدمات Static معاينة بأسماء `ai-chat-aurora-showcase-20261024` و`ai-chat-aurora-preview-20261024` و`ai-chat-sidebar-preview-20261023`، وكلها متوقفة عن Auto Deploy (`no/off`) ومربوطة بفروع معاينة/تصميم منفصلة؛ لا تعتبرها خدمات الإنتاج الأساسية.

### 11.2 مقارنة سياسة النشر

- الخدمة الحية Backend والخدمة الحية Frontend تستخدمان `autoDeploy=yes` مع `autoDeployTrigger=commit`.
- ملف `render.yaml` على `main` يحدد `autoDeployTrigger: checksPass` لكل من Backend وFrontend.
- هذه **مخالفة إعدادات مؤكدة** بين Render live وBlueprint. لم يتم تطبيق Blueprint أو تغيير الإعدادات.
- خدمة Preview Builder الحية تستخدم `commit` أيضًا، لكنها ليست معرّفة ضمن خدمات `render.yaml` الحالية؛ يلزم توثيق سبب وجودها وهل يجب إدارتها من Blueprint منفصل، ولا تضفها إلى Blueprint دون مراجعة.
- خدمة `ai-chat-redis` موجودة فعلًا في Render. لا تسجلها كخدمة مفقودة.

### 11.3 حالة كود الخدمات المنشور

أحدث deploy حي ظاهر في قائمة Render:

- Backend: deploy `dep-dbekrsla647c73ecuj00` على commit `bed46de7e8936f0cee08ae4dcc65581bee4af3da`، status `live`، مكتمل 2026-10-25 00:34 UTC.
- Frontend: deploy `dep-dbeks16bs3rs73c64pqg` على commit `63c994ed23a6ce69a3c5abf417ff6b5e145e3026`، status `live`، مكتمل 2026-10-25 00:32 UTC.
- Preview Builder: deploy `dep-dbguq6tg1s2s73ef0q2g` على commit `b690c149610a704f78d7f4ee9e6f377be7466703`، status `live`، مكتمل 2026-10-28 12:41 UTC.

**تفسير المقارنة بدل الاستنتاج من التاريخ وحده:** مقارنة Backend deploy commit مع main أظهرت أن commits الثلاثة اللاحقة تغيّر ملفات Frontend و`docs/POST_RELEASE_ROADMAP_H_TO_T_AR.md` فقط، ولا تغيّر ملفات Backend. ومقارنة Frontend deploy commit مع main أظهرت أن التغييرين اللاحقين يخصان وثائق خارطة الطريق فقط. لذلك لا يوجد في هذه المقارنة دليل على أن كود Backend أو Frontend التشغيلي متأخر عن الكود الحالي الخاص بنطاق خدمته، رغم أن SHA المنشور أقدم. لا تُجبر redeploy لمجرد اختلاف SHA.

### 11.4 إعدادات الذكاء الاصطناعي الحية

- `render.yaml` يضع افتراضيًا `AI_PROVIDER=openai` و`AI_API_BASE_URL=https://api.openai.com/v1`.
- المستخدم سبق أن قدّم إعدادًا غير سري يقول `AI_PROVIDER=gemini` مع Gemini OpenAI-compatible base URL.
- استجابة قراءة خدمة Render لم تتضمن قيم Environment Variables؛ لذلك **القيم الفعلية الحالية على Backend غير مؤكدة**. لا تستنتج أن الإنتاج يستخدم OpenAI أو Gemini من ملف Blueprint وحده.
- لا تستدعِ تحديث Environment Variables ولا تستعرض قيم أسرار. في مراجعة يدوية آمنة من لوحة الخدمة، تحقق من أسماء `AI_PROVIDER` و`AI_API_BASE_URL` و`AI_MODEL` وإعدادات embeddings، دون نسخ أي مفاتيح أو أسرار في المحادثة.

### 11.5 تشخيص فشل Frontend في CI على الرأس `b02487afacc8a96067e9a76f730486e548cfd799`

- CI run [42482552239](https://github.com/HVA09/ai-chat-app/actions/runs/42482552239): SDK وProduction Compose وPreview Builder نجحت؛ Frontend فشلت؛ Backend ظلت `in_progress` عند آخر قراءة.
- CodeQL run [42482552320](https://github.com/HVA09/ai-chat-app/actions/runs/42482552320): تحليلا Python وJavaScript/TypeScript نجحا.
- Frontend: 486 اختبارًا نجح، لكن Vitest اكتشف Unhandled Error واحدًا؛ خطوة `npm run build` تخطّتها الوظيفة بعد فشل `npm test`.
- الخطأ: `ReferenceError: window is not defined` من callback في `FilesPanel.jsx:174`، الذي ينفذ `window.setTimeout(() => setUploadProgress(null), 250)` بعد اكتمال رفع الملف.
- لا يوجد تنظيف واضح لهذا المؤقت عند إلغاء تركيب FilesPanel. يظهر أن اختبار رفع ملف المعرفة ينهي الاختبار/بيئة jsdom قبل انقضاء 250ms؛ وهذا استنتاج قوي من stack trace وطبيعة المؤقت، وليس إثباتًا نهائيًا لأي test case بعينه.
- الإصلاح المنفصل المقترح: إضافة مرجع للمؤقت وتنظيفه في effect cleanup عند unmount، مع حراسة تحديث الحالة بعد unmount، وإضافة اختبار يثبت إلغاء المؤقت/عدم تحديث الحالة بعد الإغلاق. يجب أن يكون هذا في PR كود صغير مستقل، لا في PR #671 التوثيقي.
- لا تعدّل كود FilesPanel ضمن PR #671. لا تعتبر Frontend CI ناجحًا بسبب أن 486 اختبارًا مر؛ الـunhandled error جعل الوظيفة تفشل.

### 11.6 الحالة بعد هذه القراءة

- لا تغييرات Render أو Production أو GitHub settings أو Environment Variables.
- لا redeploy تم تشغيله.
- #671 بقي Open / Draft / غير مدمج عند آخر تحقق؛ لا تجعله Ready قبل حل/تجاوز فشل Frontend بطريقة مثبتة وانتهاء Backend على HEAD الحالي.
- الخطوات التالية: (1) تحقق من اكتمال Backend run الحالية؛ (2) بعد اكتمال CI يمكن إعادة تشغيل الوظيفة الفاشلة مرة واحدة لتحديد إن كان الفشل متكررًا، دون تغيير رأس PR؛ (3) إذا تكرر، افتح PR كود مستقل لإصلاح تنظيف مؤقت FilesPanel؛ (4) تحقق/صحّح Render Auto Deploy بعد إغلاق حماية main ومراجعة السياسة؛ (5) اختبر Restore في قاعدة معزولة ثم اقبل Android ودورة الملفات.

## 12. إضافة متابعة مؤكدة — مراجعة PR #672 وتحديث حالة الفحوص — 2026-11-08

هذه الإضافة أحدث من اللقطات التاريخية السابقة في هذا الملف، وتحدّث أي حالة أقدم في الأقسام 3 و8 و10 و11 تخص PR #671 أو خطأ FilesPanel؛ تبقى المقاطع السابقة محفوظة كسجل تاريخي. لا تحذف اللقطات السابقة؛ تُحفظ لتفسير تسلسل التشخيص.

### 12.1 التحقق الحي من main والحوكمة

- تمت إعادة قراءة كائن الفرع من GitHub: main عند SHA `b690c149610a704f78d7f4ee9e6f377be7466703`.
- الاستجابة الحية: `protected=false` و`protection.enabled=false` و`required_status_checks.enforcement_level=off`، ولا توجد contexts مطلوبة.
- قائمة Repository Rulesets أعادت `[]`.
- النتيجة: حماية main لم تُفعّل بعد، وهي مانع قبل الدمج. يجب على مالك المستودع تفعيل Branch protection أو Ruleset من GitHub Settings، ثم إعادة التحقق من الحالة الحية. لا تدّعِ الحماية مفعّلة قبل ظهور دليل.

### 12.2 PR #672 — إصلاح مؤقت تقدم رفع الملفات

- الرابط: https://github.com/HVA09/ai-chat-app/pull/672
- الحالة الحية: Open / Draft / غير مدمج، و`mergeable=true`.
- الفرع: `fix/filespanel-upload-timer-cleanup-20261108`.
- HEAD: `d6216bd4d61b84fc232f848a91992ed09f0e37d3`؛ الأساس `main` عند `b690c149610a704f78d7f4ee9e6f377be7466703`.
- 3 commits، ملفان فقط، +113/-2:
  - `ai-frontend/src/components/FilesPanel.jsx`
  - `ai-frontend/src/components/FilesPanel.test.jsx`
- المراجعة الثابتة للفرق: إضافة مرجع لمؤقت تقدم الرفع، وحراسة mounted-state، وإلغاء المؤقت عند unmount، ومنع جدولة مؤقت جديد عند اكتمال الرفع بعد unmount. الاختباران الجديدان يغطّيان إلغاء المؤقت بعد جدولته، وعدم جدولته عند اكتمال upload متأخر بعد unmount. لا توجد تغييرات خارج النطاق في الفرق.
- حدود النطاق: هذا الإصلاح يمنع تحديث حالة الواجهة وجدولة المؤقت بعد unmount؛ ولا يدّعي إلغاء طلب الرفع الشبكي الجاري نفسه.

#### نتائج الفحوص المرتبطة بالرأس نفسه

- CI run [42484813720](https://github.com/HVA09/ai-chat-app/actions/runs/42484813720): الوظائف الخمس كلها `success`:
  - Frontend: 73 test files و488 tests passed؛ `npm run build` نجح.
  - Backend: `pip-audit` و`compileall` و`alembic upgrade head` نجحت؛ pytest: 520 passed و4 warnings.
  - Preview Builder: pytest وDocker build نجحا.
  - SDK: اختبارات Python وJavaScript نجحت.
  - Production Compose: التحقق من Compose وبناء صورة Backend نجحا.
- CodeQL run [42484813719](https://github.com/HVA09/ai-chat-app/actions/runs/42484813719): Python وJavaScript/TypeScript كلاهما `success`.
- لم تُسجل مراجعات GitHub أو review threads على #672 حتى آخر فحص.
- التوصية: نتيجة الكود والفحوص مشجعة للمراجعة البشرية، لكن PR يبقى Draft إلى حين استكمال بوابة حماية main وموافقة المالك. لا دمج تلقائي ولا نشر إنتاجي.

### 12.3 تفسير duplicate-key في Backend CI

- أثناء Backend CI ظهر في سجل حاوية PostgreSQL عند `2026-11-08 13:29:24.677 UTC`:
  `duplicate key value violates unique constraint "uq_scheduled_task_runs_task_scheduled_for"`.
- في نفس التشغيل اكتمل pytest بنتيجة `520 passed, 4 warnings` وبحالة Job `success`.
- تمت مطابقة اسم القيد مع الاختبار الموجود في `ai-backend/tests/test_scheduled_tasks.py`، الدالة `test_scheduled_run_slot_is_unique`: ينشئ الاختبار سجلًا أولًا ثم يحاول إدراج سجل ثانٍ للمهمة والموعد نفسيهما، ويتوقع صراحةً `IntegrityError`. هذا يطابق رسالة PostgreSQL المسجلة.
- الاستنتاج الحالي: الحدث متوقع من اختبار سلبي في CI، وليس دليلًا على خلل إنتاجي أو عيب في PR #672. لا حاجة إلى PR إصلاح مستقل بناءً على هذا السجل وحده.
- يظل التحقق مطلوبًا فقط إذا ظهر القيد نفسه في سجلات تشغيل خارج سياق الاختبارات؛ عندئذٍ تُراجع منافسة المهام/إعادة المحاولة ومسار idempotency. لا تغيّر قاعدة إنتاج.

### 12.4 PR #671 — نتائج التحقق على الرأس السابق لهذه الإضافة

- الرابط: https://github.com/HVA09/ai-chat-app/pull/671
- الحالة عند الفحص السابق لهذه الإضافة: Open / Draft / غير مدمج؛ HEAD `acc188b3d913ea75f16d9b39fb9c52200ed6bd58`؛ الملفان كلاهما داخل `docs/`.
- CI run [42482918330](https://github.com/HVA09/ai-chat-app/actions/runs/42482918330): جميع الوظائف الخمس نجحت على HEAD نفسه.
- CodeQL run [42482918372](https://github.com/HVA09/ai-chat-app/actions/runs/42482918372): تحليلا Python وJavaScript/TypeScript نجحا على HEAD نفسه.
- لا توجد مراجعات أو review threads مسجلة على #671 حتى آخر فحص.
- CI وCodeQL أعلاه يخصان الرأس `acc188...` فقط. إضافة هذا القسم إلى الفرع أنشأت commit جديدًا، لذلك أُطلقت فحوص جديدة؛ يجب اعتماد الفحوص المرتبطة بأحدث HEAD live، لا هذه النتائج السابقة، قبل تحويل PR إلى Ready.
- يجب أن يُراجع المحتوى التوثيقي النهائي قبل تحويله إلى Ready؛ لا تعتمد على أرقام/حالات الفحوص القديمة الواردة في اللقطات السابقة من هذا الملف.

### 12.5 حدود التغيير وقرار المتابعة

- هذه الإضافة توثيق داخل فرع PR #671 فقط. لا تعديل على main أو Render أو Supabase أو Environment Variables أو الأسرار أو قواعد البيانات، ولا نشر.
- يبقى تجميد الميزات الجديدة ساريًا.
- ترتيب الخطوات: (1) حماية main يدويًا من GitHub Settings ثم التحقق؛ (2) استكمال مراجعة #672 وعدم دمجه قبل موافقة صريحة منفصلة؛ (3) لا إجراء إضافي على duplicate-key إلا إذا ظهر خارج الاختبارات؛ (4) مراجعة #671 على HEAD النهائي بعد انتهاء فحوص هذا التحديث؛ (5) مواصلة بوابات H الأخرى: Restore إلى قاعدة اختبار معزولة، Android acceptance، دورة الملفات، وQueuePool/SSE تحت نشر مرحلي مضبوط.

## 13. تحديث مؤكد — تفعيل حماية main — 2026-11-08

هذا القسم أحدث من اللقطات السابقة في الأقسام 1–12، ويصحح حالة الحوكمة القديمة التي كانت تسجل أن main غير محمي. تبقى تلك اللقطات محفوظة كسجل تاريخي لتسلسل العمل، ولا تمثل الحالة الحالية.

### 13.1 نتيجة إعداد GitHub بواسطة مالك المستودع

- أنشأ مالك المستودع Classic Branch Protection Rule للفرع `main`، ثم حفظ إعداداتها بنجاح. ظهرت رسالة GitHub: `Branch protection rule settings saved.`
- أُعيدت قراءة كائن الفرع مباشرة بعد الحفظ: `protected=true` و`protection.enabled=true`.
- يظل SHA الحالي لـ`main`: `b690c149610a704f78d7f4ee9e6f377be7466703`؛ لم يتغير أثناء إعداد الحماية.
- GitHub يؤكد أن فحوص الحالة مطلوبة للجميع (`enforcement_level=everyone`) وأن contexts المطلوبة هي بالضبط:
  - `backend`
  - `frontend`
  - `sdk`
  - `preview-builder`
  - `production-compose`
- أظهرت صورة الإعدادات المحفوظة أن `Require a pull request before merging` و`Require status checks to pass before merging` و`Do not allow bypassing the above settings` مفعّلة. كما بقي `Require approvals` غير مفعّل، و`Allow force pushes` و`Allow deletions` غير مفعّلين.
- endpoint التفصيلي لقراءة branch protection أعاد 403 من تكامل GitHub، لذلك لا نزعم قراءة كل الحقول عبر API؛ التأكيد مركّب من كائن الفرع الحي، وقائمة الفحوص المطلوبة فيه، وصور GitHub التي عرضت الخيارات ورسالة الحفظ.
- واجهة Repository Rulesets أعادت `[]`؛ هذا لا ينفي الحماية، لأن الحماية المفعلة هنا هي Classic Branch Protection Rule وليست Repository Ruleset.

### 13.2 حالة طلبَي السحب بعد تفعيل الحماية

- PR #672: Open / Draft / غير مدمج، HEAD `d6216bd4d61b84fc232f848a91992ed09f0e37d3`. CI run [42484813720](https://github.com/HVA09/ai-chat-app/actions/runs/42484813720) وجميع وظائفه الخمس نجحت؛ CodeQL run [42484813719](https://github.com/HVA09/ai-chat-app/actions/runs/42484813719) نجح لتحليلي Python وJavaScript/TypeScript.
- PR #671: Open / Draft / غير مدمج، HEAD `2bab1b7bd7916bebe00fbafe01d5399f6fc2024b`. CI run [42488818392](https://github.com/HVA09/ai-chat-app/actions/runs/42488818392) نجح في الوظائف الخمس؛ CodeQL run [42488818393](https://github.com/HVA09/ai-chat-app/actions/runs/42488818393) نجح للتحليلين.
- بيانات GitHub المباشرة أكدت أن كِلا الطلبين ما زالا Draft ومفتوحين وغير مدمجين، وأن رأسيهما لم يتغيرا في هذا التحقق.
- لا تعتبر فحوص #671 الحالية صالحة بعد إضافة هذا القسم؛ تحديث الملف سينشئ HEAD جديدًا ويستلزم انتظار CI وCodeQL على ذلك الرأس النهائي.
- لم يحدث دمج أو نشر أو تعديل على Render أو Supabase أو الأسرار أو قواعد بيانات الإنتاج.

### 13.3 الخطوة التالية

1. إعادة تشغيل/قراءة CI وCodeQL تلقائيًا على HEAD الجديد لـ#671 بعد توثيق هذا التحديث.
2. إجراء المراجعة النهائية للكود والاختبارين في #672؛ يظل Draft إلى حين قرار المستخدم الصريح. لا يُدمج لمجرد نجاح CI.
3. بعد ذلك تُستكمل بوابات H الأخرى: Restore إلى قاعدة اختبار معزولة، مراجعة Auto Deploy الحي في Render دون تعديل، Android acceptance، دورة الملفات، ومراقبة QueuePool/SSE باختبار مرحلي مضبوط.
4. الميزات الجديدة تظل مجمدة، ولا تغيير على `main` أو الإنتاج دون موافقة منفصلة محددة.


## 14. إغلاق فحوص HEAD السابق بعد تفعيل الحماية — 2026-11-08

- أُعيد فحص PR #671 ورأسه `cb22b6b8d01a02098a4913d76201ea59eceb11cd`؛ بقي Open / Draft / غير مدمج.
- CI run [42496215664](https://github.com/HVA09/ai-chat-app/actions/runs/42496215664) اكتمل بنجاح على هذا الرأس، وجميع الوظائف الخمس نجحت: backend وfrontend وsdk وpreview-builder وproduction-compose.
- Backend job logs تؤكد: `520 passed, 4 warnings in 204.93s`. كما نجحت `pip-audit` و`compileall` و`alembic upgrade head`. التحذيرات الأربعة تشمل deprecation في `crypt` وStarlette، وتحذير SQLAlchemy عن transaction already deassociated؛ ليست حالات فشل للاختبارات.
- CodeQL run [42496215661](https://github.com/HVA09/ai-chat-app/actions/runs/42496215661) اكتمل بنجاح؛ تحليلا Python وJavaScript/TypeScript نجحا. كذلك ظهرت check باسم `CodeQL` بحالة success.
- تنبيه حوكمة: قراءة كائن `main` تؤكد أن required status contexts الحالية هي فقط الخمسة CI المذكورة أعلاه. نتائج CodeQL ناجحة لكنها **ليست حاليًا ضمن required status checks**. التوصية هي إضافة السياستين الدقيقتين `Analyze (python)` و`Analyze (javascript-typescript)` إلى Branch protection بعد ظهورهما في قائمة الفحوص، ثم إعادة قراءة كائن الفرع للتحقق؛ لا تعتبر CodeQL إلزاميًا قبل ذلك.
- PR #672 ما زال Open / Draft / غير مدمج على HEAD `d6216bd4d61b84fc232f848a91992ed09f0e37d3`، وCI وCodeQL السابقان على ذلك الرأس ناجحان.
- `main` ما زال محميًا عند SHA `b690c149610a704f78d7f4ee9e6f377be7466703`; لم يحدث دمج أو نشر أو تعديل على Render/Supabase أو قواعد بيانات الإنتاج.
- هذه النتائج تخص HEAD `cb22b6b...`؛ أي تحديث لاحق للفرع التوثيقي ينشئ HEAD جديدًا ويستلزم اعتماد فحوصه هو، لا إعادة استخدام هذه النتائج.


## 15. نتيجة التحقق المكتملة على HEAD 9367cf0 — 2026-11-08

- أُعيد فحص PR #671 بعد اكتمال CI وCodeQL على HEAD `9367cf0757e7426a26ebc9720c2e7624c7827645`.
- CI [42497065942](https://github.com/HVA09/ai-chat-app/actions/runs/42497065942): جميع الوظائف الخمس نجحت؛ Backend اكتملت بعد `pytest -q`.
- CodeQL [42497065912](https://github.com/HVA09/ai-chat-app/actions/runs/42497065912): تحليلا Python وJavaScript/TypeScript نجحا.
- فحوص Backend في هذا التشغيل: `pip-audit` و`compileall` و`alembic upgrade head` نجحت، وpytest: `520 passed, 4 warnings in 204.93s`.
- أُعيد تأكيد حماية `main`: `protected=true`، وcontexts المطلوبة للجميع هي `backend`, `frontend`, `sdk`, `preview-builder`, `production-compose`. لم يتغير main عن SHA `b690c149610a704f78d7f4ee9e6f377be7466703`.
- PR #672 باقٍ Open / Draft / غير مدمج، HEAD `d6216bd4d61b84fc232f848a91992ed09f0e37d3`؛ check-runs الخمسة وCodeQL على رأسه ناجحة. تمت مراجعة patch: تغييران محصوران في FilesPanel واختباراته، دون تغييرات خارج النطاق. لا توجد reviews أو review threads مسجلة.
- حدّثنا وصف PR #671 ليشير إلى نتيجة HEAD `9367cf0` وإلى أن CodeQL ناجح لكنه غير مطلوب ضمن branch protection الحالية.
- أي commit توثيقي جديد بعد هذا السجل سيُنشئ HEAD مختلفًا؛ يجب التحقق من CI وCodeQL على ذلك الرأس نفسه. لا تعِد استخدام نجاحات HEAD `9367cf0` لإثبات فحوص commit أحدث.
- لم يحدث دمج أو نشر أو تعديل على Render/Supabase أو متغيرات البيئة أو قواعد بيانات الإنتاج. تبقى الميزات الجديدة مجمدة.


## 16. تحديث الحماية — جعل CodeQL إلزاميًا — 2026-11-08

هذا التحديث يصحح أي فقرة سابقة في السجل كانت تقول إن CodeQL ناجح لكنه غير مطلوب؛ تلك الفقرات تصف الحالة قبل تعديل مالك المستودع لقاعدة الحماية.

- حفظ مالك المستودع تحديث Branch protection rule على `main`، وأظهرت واجهة GitHub رسالة `Branch protection rule settings saved.`
- أعادت قراءة GitHub المباشرة بعد الحفظ: `protected=true` و`protection.enabled=true`، و`required_status_checks.enforcement_level=everyone`.
- أصبحت contexts السبعة المطلوبة بالضبط:
  1. `backend`
  2. `frontend`
  3. `sdk`
  4. `preview-builder`
  5. `production-compose`
  6. `Analyze (python)`
  7. `Analyze (javascript-typescript)`
- رأس `main` ما زال `b690c149610a704f78d7f4ee9e6f377be7466703`؛ لا يوجد commit أو merge على main نتيجة تغيير الحماية.
- على PR #671، الرأس `8ffe0e1feb8c07c95eee65ad64cff11b1f3e1c97` اجتاز CI [42497639597](https://github.com/HVA09/ai-chat-app/actions/runs/42497639597) وCodeQL [42497639580](https://github.com/HVA09/ai-chat-app/actions/runs/42497639580) بنجاح. هذه الفحوص تخص الرأس المذكور تحديدًا.
- PR #672 ما زال Open / Draft / غير مدمج على HEAD `d6216bd4d61b84fc232f848a91992ed09f0e37d3`، وفحوصه السابقة على هذا الرأس ناجحة.
- لم يحدث دمج أو نشر أو تعديل على Render أو Supabase أو متغيرات البيئة أو قواعد بيانات الإنتاج. تجميد الميزات مستمر.
- إذا أُضيف commit جديد إلى فرع #671 لتحديث هذا السجل، فيجب اعتماد CI وCodeQL على الرأس الجديد قبل Ready أو الدمج؛ لا تُستخدم نتائج `8ffe0e1` لتغطية رأس مختلف.

## 17. تحديث استقرار الملفات وRender — 2026-11-08

### 17.1 PR #672 — توسيع إصلاح unmount لقائمة الرفع

- الحالة الحية: Open / Draft / غير مدمج، mergeable=true.
- HEAD: 0731d6e5e895a080cc3ac66c31a69401d9946db6؛ 5 commits؛ ملفان فقط؛ +145/-2.
- الملفات: ai-frontend/src/components/FilesPanel.jsx وai-frontend/src/components/FilesPanel.test.jsx.
- أثناء المراجعة وُجدت حالة إضافية: إذا رفع المستخدم عدة ملفات وأزال FilesPanel أثناء رفع أول ملف، كان loop يمكن أن يبدأ upload للملف التالي بعد unmount.
- أُضيف guard في بداية كل iteration: إذا لم يعد المكوّن mounted، يتوقف loop قبل بدء ملف جديد. لا يدّعي التغيير إلغاء طلب الرفع الشبكي الجاري بالفعل.
- أُضيف اختبار ثالث يثبت أن الملف التالي لا يبدأ بعد unmount أثناء رفع الأول. الاختبارات الثلاثة الجديدة تغطي: عدم بدء الملفات المتبقية، تنظيف مؤقت تقدم الرفع، وعدم جدولة المؤقت إذا اكتمل upload بعد unmount.
- نتائج CI [42498986649](https://github.com/HVA09/ai-chat-app/actions/runs/42498986649): جميع الوظائف الخمس نجحت.
  - Frontend: 73 test files و489 tests passed؛ npm run build نجح.
  - Backend: pip-audit وcompileall وalembic upgrade head نجحت؛ pytest: 520 passed, 4 warnings.
  - Preview Builder: pytest وDocker build نجحا.
  - SDK: اختبارات Python وJavaScript نجحت.
  - Production Compose: validation وبناء Backend image نجحا.
- CodeQL [42498986713](https://github.com/HVA09/ai-chat-app/actions/runs/42498986713): تحليلا Python وJavaScript/TypeScript نجحا.
- رسالة PostgreSQL duplicate-key على uq_scheduled_task_runs_task_scheduled_for تطابق الاختبار السلبي test_scheduled_run_slot_is_unique في ai-backend/tests/test_scheduled_tasks.py، الذي يتوقع صراحةً IntegrityError عند إدخال سجل مكرر. لا تعد الرسالة وحدها دليلًا على عطل إنتاجي.
- لم تُسجل مراجعات GitHub أو review threads على #672 عند آخر تحقق. يظل Draft حتى مراجعة المالك وقبول Android/الملفات في بيئة الاستخدام؛ نجاح CI لا يساوي قبولًا إنتاجيًا.

### 17.2 تحقق Render حي — لقطة تاريخية للقراءة فقط قبل تعديل Auto Deploy

تم استخدام workspace المؤكد My Workspace (ID tea-dagsi5ou01pc73f2g470) دون أي تغييرات:

| الخدمة | الفرع | Auto Deploy | Trigger الحي |
|---|---|---|---|
| ai-chat-backend | main | yes | commit |
| ai-chat-frontend | main | yes | commit |
| ai-chat-preview-builder | main | yes | commit |

- render.yaml على main يحدد autoDeployTrigger: checksPass لكل من ai-chat-backend وai-chat-frontend. توجد إذن مخالفة إعداد حية: commit مقابل checksPass.
- ai-chat-preview-builder خدمة حيّة لكنها غير معرفة في render.yaml الحالي. لا تضفها أو تطبق Blueprint قبل تقرير ما إذا كانت خدمة دائمة مستقلة أو موردًا تجريبيًا.
- Backend وFrontend مربوطتان بـmain وAuto Deploy مفعّل. لا يعني هذا أنهما نُشرتا بعد تغييرات PR #672؛ PR ما زال Draft وغير مدمج.
- قائمة Render Postgres في مساحة العمل أعادت No Postgres instances found. هذا لا يعني فقد قاعدة الإنتاج: render.yaml يذكر أن PostgreSQL خارجي عبر Supabase وDATABASE_URL قيمة سرية خارج Blueprint. لا تختبر الإنتاج ولا تستنتج حالة Supabase من غياب Render Postgres.
- Redis / Key Value ai-chat-redis موجود وحالته available على الخطة المجانية في Ohio؛ persistence mode off وسياسة الذاكرة allkeys_lru وفق الإعداد الحي.
- قائمة أحداث Backend وFrontend أعادت [] ضمن نافذة الاستعلام الافتراضية (آخر 7 أيام). لا تثبت غياب حوادث أقدم.
- **تنبيه زمني:** جدول Trigger أعلاه يسجل لقطة التدقيق السابقة لتعديل المالك في 2026-11-08؛ الحالة الحية الأحدث موثقة في القسم 18، وهو المرجع الحالي.
- أداة قراءة الخدمة لم تعرض Environment Variables. لذلك لا تزال قيمة AI_PROVIDER الحية غير مؤكدة؛ لا تستنتج أنها OpenAI أو Gemini من render.yaml أو من إعداد قدّمه المستخدم سابقًا. لم تُقرأ أسرار أو مفاتيح.
- لم يحدث Deploy أو Restart أو Blueprint sync أو تعديل Auto Deploy أو Environment Variables أو Database أو Redis. التحقق كله قراءة فقط.

### 17.3 الخطوات التالية

1. PR #672 لديه فحوص CI وCodeQL ناجحة على HEAD 0731d6e؛ أبقه Draft لحين قرار المالك وقبول Android/دورة الملفات. لا دمج تلقائي.
2. PR #671 وثائقي؛ حدّث هذا السجل ثم تحقق من CI/CodeQL على آخر HEAD جديد قبل Ready.
3. تمت مواءمة Auto Deploy على Backend وFrontend مع checksPass بتغيير مباشر من المالك في Render؛ تفاصيل التحقق الحي في القسم 18. لم يتم استخدام Blueprint sync.
4. راجع خدمة Preview Builder المنفصلة قبل أي Blueprint sync.
5. استكمل Restore اختباريًا إلى قاعدة Supabase معزولة، ثم Android acceptance، دورة الملفات، وQueuePool/SSE staging. لا تشغيل على قاعدة الإنتاج.
6. يبقى تجميد الميزات الجديدة ساريًا. لا تعديل على main أو خدمات الإنتاج دون موافقة منفصلة محددة.

## 18. تحديث إعداد Auto Deploy بعد موافقة المالك — 2026-11-08

نفّذ المالك تغيير إعداد Auto Deploy يدويًا من لوحة Render، ثم أُعيد التحقق عبر قراءة تفاصيل الخدمتين مباشرة. النتيجة الحية:

| الخدمة | الفرع | Auto Deploy | Trigger الحي | آخر تحديث للإعداد |
|---|---|---|---|---|
| ai-chat-backend | main | yes | checksPass | 2026-11-08 16:49:58 UTC |
| ai-chat-frontend | main | yes | checksPass | 2026-11-08 16:52:31 UTC |

- تحقق مستقل: استجابة Render لكل خدمة تؤكد `autoDeploy=yes` و`autoDeployTrigger=checksPass` والفرع `main`.
- هذا يطابق `render.yaml` على `main` بالنسبة إلى Backend وFrontend.
- لم يتغير إعداد `ai-chat-preview-builder`، ولا تزال خارج نطاق هذا التعديل.
- لم يحدث Deploy يدوي أو Restart أو Blueprint sync، ولم تتغير Environment Variables أو الأسرار أو قاعدة البيانات أو Redis.
- الإعداد `After CI Checks Pass` يتحكم في توقيت Auto Deploy فقط؛ لا يعني أن PRs المفتوحة أو Draft تم دمجها أو نشرها.
- PR #671 وPR #672 يظلان Draft وغير مدمجين إلى أن يراجع المالك ويصدر موافقة مستقلة على كل PR. لا تعتبر موافقة إعداد Render موافقة دمج.
- فحوص PR #671 على HEAD السابق `aba81282d3ecb9da200cc8ad6478a61e09144e89` اكتملت بنجاح: CI run `42499577766` بجميع الوظائف الخمس، وCodeQL run `42499577781` بتحليلي Python وJavaScript/TypeScript. أي تحديث توثيقي جديد ينشئ HEAD جديدًا ويتطلب إعادة فحوصه.


## 19. مراجعة PR #664 وإغلاق جولة التحقق الحالية — 2026-11-08

### 19.1 PR #664 — إصلاح QueuePool/SSE

- الحالة: Open / Draft / غير مدمج؛ `mergeable=true`.
- HEAD الحالي: `35ef8e6882e562305e07049d3c1af4b024891ba9`.
- مقارنة الفرع مع `main` الحالي: `ahead_by=13`, `behind_by=0`; نقطة الدمج المشتركة هي `main` عند `b690c149610a704f78d7f4ee9e6f377be7466703`. لا توجد حاجة Rebase ظاهرة في المقارنة الحالية.
- الملفات الثلاثة: `ai-backend/app/routers/chat.py`، `ai-backend/tests/test_chat.py`، `docs/POST_RELEASE_ROADMAP_H_TO_T_AR.md`.
- CI [41132462301](https://github.com/HVA09/ai-chat-app/actions/runs/41132462301): وظائف Backend وFrontend وSDK وPreview Builder وProduction Compose كلها `success`.
- CodeQL [41132462064](https://github.com/HVA09/ai-chat-app/actions/runs/41132462064): تحليلا Python وJavaScript/TypeScript كلاهما `success`.
- أُضيفت تغطية لاختبار QueuePool فعلي مبني على SQLite لإثبات رجوع checkout إلى الصفر مع بقاء القيم المحمّلة قابلة للقراءة، وتغطية ترتيب تحرير الاتصال قبل إنشاء `StreamingResponse` لفروع `chat_stream` الخمسة، إضافة إلى مساري `regenerate_chat_stream` و`edit_chat_stream`.
- مراجعة النطاق وجدت حدًا يجب عدم إخفائه: الاتصال يُحرّر قبل إنشاء استجابة SSE والبث الطويل، لكنه قد يظل محجوزًا خلال بعض awaits السابقة للاستجابة مثل RAG query embedding داخل `_augment_message()` أو `search_web()`. وثّق هذا القيد في وصف PR؛ الإصلاح تقليل محدد لوقت حجز الاتصال أثناء البث، وليس إثباتًا أن كل المسارات غير المتزامنة خالية من الاحتفاظ بالاتصال.
- لا توجد مراجعات GitHub أو review threads مسجلة على PR عند الفحص. تم تحديث وصف PR لذكر نتائج الفحوص الحالية وحدود النطاق، مع إبقائه Draft.
- لا يوجد اختبار ضغط متزامن على staging ولا مراقبة بعد نشر لهذا الرأس. لذلك لا نعلن انتهاء مشكلة QueuePool في الإنتاج، ولا ندمج أو ننشر #664 حتى تكتمل بوابة staging والقبول التشغيلي.

### 19.2 PR #671 — اكتمال الفحوص على HEAD السابق

- HEAD `dfb946b37ada78a91a1ca3e90fe783167e189b79`: CI [42502185750](https://github.com/HVA09/ai-chat-app/actions/runs/42502185750) اكتمل بنجاح في وظائفه الخمس، بما فيها Backend.
- CodeQL [42502185756](https://github.com/HVA09/ai-chat-app/actions/runs/42502185756) اكتمل بنجاح في تحليلي Python وJavaScript/TypeScript.
- إذا أضيف أي تحديث توثيقي بعد هذا السجل، فسيتغير HEAD ويجب إعادة اعتماد الفحوص على الرأس الجديد قبل اعتباره أخضر.

### 19.3 القرار والخطوات التالية

1. إبقاء #664 و#671 و#672 Draft وغير مدمجة. إعداد Render `checksPass` أو نجاح CI ليس موافقة دمج.
2. إجراء اختبار QueuePool/SSE مضبوط على staging مع قياس عدد الاتصالات المحجوزة، زمن الانتظار، وأخطاء Timeout قبل/بعد؛ لا تستخدم قاعدة الإنتاج لهذا الاختبار.
3. إجراء قبول Android ودورة الملفات الفعلية على بيئة آمنة قبل دمج تغيير FilesPanel.
4. إكمال استعادة Supabase إلى قاعدة معزولة واختبار النسخ الاحتياطي/الاستعادة دون تعديل قاعدة الإنتاج.
5. يظل تجميد الميزات الجديدة قائمًا. لا تغيّر `main` أو Render أو Supabase أو الأسرار أو الموارد دون موافقة مستقلة محددة.


## 20. نتائج الاختبار التكاملي لـPostgreSQL ومراجعة الحواجز — 2026-11-08

### 20.1 اكتمال PR #664 على الرأس الحالي

- HEAD: `97933094ab3573b24070234cad7aa148ce82af94`.
- CI [42504844968](https://github.com/HVA09/ai-chat-app/actions/runs/42504844968): الوظائف الخمس كلها `success` (Backend وFrontend وSDK وPreview Builder وProduction Compose).
- CodeQL [42504844942](https://github.com/HVA09/ai-chat-app/actions/runs/42504844942): Python وJavaScript/TypeScript كلاهما `success`.
- سجل Backend النهائي: `525 passed, 4 warnings in 296.46s`، ولا يوجد Failed tests.
- الاختبار الإضافي في `ai-backend/tests/test_chat.py` ينشئ QueuePool مستقلًا بحجم اتصال واحد ويستخدم `TEST_DATABASE_URL` فقط. يرفض أي عنوان مضيف بعيد، ويسمح فقط بـ`localhost` أو `127.0.0.1`، لذلك لا يمكن لهذا الاختبار أن يتصل بـSupabase أو بقاعدة إنتاج بعيدة. في GitHub Actions يشير المتغير إلى PostgreSQL service المؤقت الخاص بالـCI.
- التحقق العملي داخل الاختبار: الجلسة الأولى تحصل على الاتصال، ثم يقوم helper بتحريره؛ بعدها تستطيع جلسة ثانية الحصول على الاتصال الوحيد وتنفيذ استعلام، مع بقاء كائن Session الأول موجودًا. بعد إغلاق الثانية تعيد الأولى الحصول على اتصال عندما تحتاج إلى حفظ لاحق.
- هذا يثبت سلوك تحرير الاتصال في اختبار PostgreSQL معزول، ولا يحاكي ضغط إنتاج متعدد المستخدمين ولا يثبت زوال كل حالات QueuePool في Render.
- مقارنة الفرع بـ`main`: `ahead_by=15`, `behind_by=0`؛ لا توجد حاجة Rebase ظاهرة. الملفات المعدلة ما زالت ثلاثة: `chat.py` و`test_chat.py` وخارطة H-to-T.
- PR #664 يبقى Open / Draft / غير مدمج إلى أن تتم مراجعة المالك والبوابات التشغيلية.

### 20.2 متابعة حدود إصلاح SSE

- PR #664 يعالج الاحتفاظ بالاتصال أثناء انتظار مولّد SSE بعد بناء `StreamingResponse`.
- لا يغطي جميع فترات الانتظار السابقة لإنشاء الاستجابة. مراجعة الكود أظهرت `_augment_message()` قد ينتظر RAG query embedding، ومسار البحث ينتظر `search_web()` قبل إصدار الاستجابة.
- فتحت [Issue #674](https://github.com/HVA09/ai-chat-app/issues/674) لقياس ومعالجة هذه الفترات باختبارات PostgreSQL bounded-pool، مع اختبار حالات الاستثناء والمهلة وانقطاع العميل. لا تغيّر Agent-mode دون مراجعة مستقلة لأن الأدوات قد تحتاج DB أثناء التنفيذ.

### 20.3 حماية استعادة النسخ الاحتياطية

- فتحت [Issue #673](https://github.com/HVA09/ai-chat-app/issues/673) بعد مراجعة `.github/workflows/restore-to-supabase.yml`.
- الملف يستخدم `SUPABASE_DB_URL` مع `pg_restore --clean --if-exists`. لم تُقرأ قيمة السر ولم تُشغّل الـworkflow؛ لا نعرف من قراءة آمنة ما إذا كانت الوجهة غير إنتاجية.
- المشروع الفعلي `ai-chat-prod-db` حالته `ACTIVE_HEALTHY`، ولا توجد Supabase branches حاليًا.
- المنظمة على Free، وتكلفة فرع Supabase المعروضة هي `$0.01344/hour`. لم ننشئ فرعًا ولم نوافق على أي تكلفة.
- ممنوع تشغيل استعادة تجريبية قبل فصل الوجهة والتحقق من المشروع/hostname بقائمة سماح ورفض صريح لمعرّف الإنتاج، مع حماية خاصة لأي استعادة إنتاجية.

### 20.4 ملاحظات تشغيل Render

- القراءة الحية تؤكد Backend وFrontend على `main` مع `autoDeploy=yes` و`autoDeployTrigger=checksPass`; Preview Builder بقي `commit` وخارج نطاق التغيير.
- حدث Render تاريخي واحد للخلفية: `server_failed` بسبب HTTP health check timeout بعد 5 ثوانٍ عند `2026-10-25 17:07:57 UTC`، وتلاه `server_available` عند `17:09:38 UTC`. نسجله كحادثة تعافت، وليس عطلًا حاليًا.
- لا توجد أحداث فشل مماثلة في صفحة أحداث Frontend التي فُحصت. محاولة قراءة application logs الحالية تعذرت بسبب Loki `503`; لا يجوز الاستنتاج أن أخطاء QueuePool غير موجودة حاليًا.
- لم يحدث Deploy أو Restart أو Blueprint sync أو تعديل أسرار أو Environment Variables أو قاعدة الإنتاج أو Redis.

### 20.5 بوابات لا تزال مفتوحة

1. قبول Android ورحلة رفع/قراءة/ربط/حذف الملفات فعليًا؛ هذا لا يُستبدل بـCI.
2. staging دائم أو اختبار محلي معزول ببيانات اختبار لتنفيذ ضغط SSE/QueuePool وقياس checkout wait/hold duration وأخطاء Timeout. لا تستخدم Render production أو Supabase production.
3. إغلاق Issue #674 باختبارات للفترات السابقة للاستجابة.
4. إغلاق Issue #673 قبل أي restore workflow.
5. إبقاء #664 و#671 و#672 Draft حتى المراجعة والموافقة المنفصلة؛ نجاح CI لا يمنح إذن دمج.
