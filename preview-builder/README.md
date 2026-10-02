# Isolated Preview Builder

هذا المكوّن خدمة منفصلة عن ai-backend. لا تضف Node أو npm إلى صورة الـbackend.

## الوضع الافتراضي

التنفيذ الحقيقي للـbuild مغلق ما لم يتم ضبط:
- BUILDER_ENABLE_BUILDS=true
- BUILDER_TOKEN
- وجود bubblewrap (bwrap)

الخدمة ترفض أي طلب غير مصادق عليه، وتقبل فقط البروتوكول X-Preview-Protocol: 1 والأمر الثابت npm run build.

## العزل

تثبيت الاعتمادات يستخدم npm ci/install --ignore-scripts.

هذا يمنع lifecycle scripts أثناء مرحلة تثبيت الحزم. مرحلة npm run build تعمل داخل bubblewrap مع:
- network namespace معزول (لا شبكة من عملية build)
- filesystem مقيد للقراءة مع workspace قابل للكتابة
- user/process/ipc/uts namespaces معزولة
- حدود زمنية للـinstall والـbuild
- حاوية non-root مع cap_drop: ALL و no-new-privileges
- حدود CPU وRAM وPIDs في Compose

## نشر مهم

لا تشارك أسرار الـbackend أو قاعدة البيانات أو Redis مع Builder. ضعه خلف HTTPS وبمصادقة token، ولا تعرض منفذ الإدارة للعامة.

هذه المرحلة تنشئ builder مستقلًا فقط. طبقة الواجهة التي تفك ZIP وتخدم الأصول ستأتي لاحقًا.
