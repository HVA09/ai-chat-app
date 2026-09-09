# AI Backend

Backend لتطبيق مساعد ذكاء اصطناعي (شات بوت)، مبني بـ FastAPI + PostgreSQL،
مع مصادقة JWT، صلاحيات حسب الدور، حد استخدام يومي، اختبارات، Docker، Nginx، وCI/CD.

## البنية

```
app/
  main.py          نقطة التشغيل — يجمع كل شيء
  config.py        الإعدادات (من .env)
  database.py      اتصال SQLAlchemy
  dependencies.py  المستخدم الحالي / صلاحية admin / الحد اليومي
  models/          جداول DB: User, Conversation, Message, UsageLog, FileAttachment,
                   AuditLog, Plan, Subscription, Notification
  schemas/         Pydantic (تحقق من البيانات الداخلة/الخارجة)
  auth/            تشفير كلمات المرور + JWT + 2FA (TOTP) + مسارات /auth
  routers/         /users /chat /conversations /admin /billing /files /notifications
  services/
    ai_providers/       OpenAI/Anthropic/Gemini/DeepSeek — واجهة موحّدة لمحرك AI
    payment_providers/  Stripe/PayPal — واجهة موحّدة للدفع والاشتراكات
    email_service.py    إرسال الإيميل (SMTP أو طباعة باللوق بوضع التطوير)
  cache.py, tasks.py, audit.py   Redis caching، Celery للإيميل بالخلفية، سجل تدقيق
migrations/        Alembic — 8 migrations من الجدول الأساسي حتى الإشعارات
tests/             pytest — auth, chat, conversations, admin, billing, files,
                   notifications (REST + WebSocket), 2FA, profile, account security,
                   ai providers/streaming, performance/caching (كلها مع mock لمحرك AI)
nginx/nginx.conf   reverse proxy + rate limiting + دعم WebSocket لـ /ws/
.github/workflows/ CI/CD عبر GitHub Actions
Dockerfile, docker-compose.yml (app, db, redis, celery_worker, nginx, certbot, backup)
```

## قبل التشغيل — لازم تجهّزه بنفسك

انسخ `.env.example` إلى `.env` واملأ:

- `POSTGRES_PASSWORD` — كلمة مرور قاعدة البيانات
- `JWT_SECRET_KEY` — قيمة عشوائية طويلة (`openssl rand -hex 32`)
- `AI_API_KEY` — مفتاحك الخاص من مزوّد الذكاء الاصطناعي (OpenAI أو غيره).
  بدون مفتاح حقيقي هنا، مسار `/chat` لن يعمل.

## التشغيل محليًا

```bash
cp .env.example .env   # ثم عدّل القيم
docker compose up --build
```

- الـ API يصير متاح عبر Nginx على `http://localhost`
- توثيق تفاعلي (Swagger): `http://localhost:8000/docs` (مباشرة على منفذ FastAPI أثناء التطوير)

أهم المسارات:

| المسار | الوصف |
|---|---|
| POST `/auth/register` | تسجيل مستخدم جديد |
| POST `/auth/login` | تسجيل الدخول → access + refresh token |
| POST `/auth/refresh` | تجديد access token |
| GET `/users/me` | بيانات المستخدم الحالي (يحتاج توكن) |
| POST `/chat` | إرسال رسالة للمساعد (يحتاج توكن) |
| GET `/conversations` | قائمة محادثات المستخدم (يحتاج توكن) |
| GET `/conversations/{id}` | تفاصيل محادثة ورسائلها (يحتاج توكن) |
| GET `/admin/stats` | إحصائيات (يحتاج دور admin) |

للدخول في Swagger: نفّذ `/auth/login`، وانسخ `access_token`، والصقه في زر Authorize
(بصيغة `Bearer <التوكن>`).

## ربط الفرونت اند (React + Vite)

- `CORS_ORIGINS` مضبوط افتراضيًا على `http://localhost:5173` (منفذ Vite dev server)
- منفذ 8000 منشور على الجهاز مباشرة في docker-compose، فمشروع الفرونت (`.env.development`
  فيه `VITE_API_BASE_URL=http://localhost:8000`) يوصله بدون أي إعداد إضافي
- عند النشر: حدّث `CORS_ORIGINS` ليشمل دومين الفرونت الحقيقي

## الاختبارات

تحتاج قاعدة بيانات PostgreSQL منفصلة للاختبار:

```bash
pip install -r requirements-dev.txt
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_backend_test
pytest -v
```

استدعاء محرك AI تم عمل mock له في الاختبارات، فما تحتاج مفتاح API حقيقي عشان تشغّلها.

## CI/CD

عند كل push على `main`: تشغيل الاختبارات → بناء صورة Docker → رفعها لـ GitHub
Container Registry → محاولة نشر عبر SSH على سيرفرك.

خطوة النشر (`deploy`) لن تعمل قبل ما تضيف Secrets حقيقية في إعدادات الريبو
(`Settings → Secrets and variables → Actions`): `SERVER_HOST`, `SERVER_USER`,
`SSH_PRIVATE_KEY` — حسب أي سيرفر Cloud تستخدمه (AWS EC2 / Azure VM / GCP Compute
Engine كلها تصلح، لأن الخطوة تتعامل معه كسيرفر Linux عادي عبر SSH).

## قاعدة البيانات (Alembic)

الجداول تُدار الآن عبر migrations بدل الإنشاء التلقائي. أول تشغيل (والحاويات
تسويها تلقائيًا عبر Dockerfile):

```bash
alembic upgrade head
```

لو عدّلت أي model، ولّد migration جديدة:

```bash
alembic revision --autogenerate -m "وصف التعديل"
alembic upgrade head
```

## ملاحظات

- أول إيميل يسجّل بالنظام يصير `admin` تلقائيًا (ما فيه لوحة ترقية مستخدمين بعد) —
  سجّل حسابك الشخصي أول واحد. حساب الـ admin معفى من الحد اليومي لطلبات AI.
- `Base.metadata.create_all` يُنشئ الجداول تلقائيًا عند التشغيل — مناسب للتعلّم.
  لمشروع أكبر، الخطوة التالية المنطقية هي Alembic لإدارة migrations.
- كل الأسرار تُقرأ من متغيرات بيئة فقط، ولا يوجد أي مفتاح مكتوب داخل الكود.
- أي خطأ غير متوقع يُسجَّل (logging) ويرجع للمستخدم برسالة عامة بدون تفاصيل داخلية.
- تسجيل الدخول محمي من Brute Force: 5 محاولات فاشلة تقفل الحساب 15 دقيقة (قابلة للتعديل).
- الإيميلات (تأكيد البريد، إعادة تعيين كلمة المرور) تُطبع باللوق ما لم تضبط SMTP —
  شغّل السيرفر وشوف رابط التأكيد بالـ terminal مباشرة.
- Two Factor Authentication (TOTP): `/auth/2fa/setup` يرجّع QR code + سر للإدخال اليدوي،
  `/auth/2fa/enable` يفعّله بعد تأكيد رمز صحيح. لو مفعّل، `/auth/login` يرجع 428 لو ما
  أرسلت `totp_code` مع بيانات الدخول.
- Rate Limiting بـ Nginx: 5 طلبات/دقيقة على `/auth/*`، 60 طلب/دقيقة على باقي المسارات.
- محرك AI متعدد المزوّدين: `AI_PROVIDER` بـ `.env` يقبل `openai`, `anthropic`, `gemini`, `deepseek`
  (كل مزوّد صيغة API مختلفة تمامًا — التبديل بينهم فقط بتغيير `.env`، بدون لمس الكود).
- `POST /chat/stream` يرجّع الرد تدريجيًا (Server-Sent Events) بدل انتظار الرد كامل.
- رفع الملفات: `POST /files/upload` (صور، PDF، Word، Excel، CSV — حتى `MAX_UPLOAD_SIZE_MB`).
  تُخزَّن على القرص داخل الحاوية (`UPLOAD_DIR`)، مربوطة بـ volume دائم في docker-compose.
- لوحة إدارة (admin فقط): `/admin/stats`، `/admin/users` (عرض/تعديل/حذف)،
  `/admin/conversations` (عرض/حذف أي محادثة)، `/admin/logs` (سجل تدقيق للأحداث المهمة —
  تسجيل، دخول فاشل، قفل حساب، حذف، تعديلات إدارية...).
- الاشتراكات: خطتان جاهزتان (Free, Pro) — الحد اليومي لطلبات AI يتغيّر تلقائيًا حسب خطة
  المستخدم الفعّالة. **قبل ما يشتغل الدفع فعليًا** لازم:
  1. تنشئ منتج/سعر بحساب Stripe (أو خطة بحساب PayPal) وتحدّث `stripe_price_id`
     (أو `paypal_plan_id`) بجدول `plans` يدويًا أو عبر migration جديدة
  2. تعبّي `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` (أو مفاتيح PayPal) بـ `.env`
  3. تضبط webhook بلوحة Stripe/PayPal يشاور على `https://<دومينك>/billing/webhook/stripe`
     (أو `/paypal`)
  جرّب بوضع Sandbox/Test أول قبل أي مفاتيح حقيقية.
- تتبّع توكنز الذكاء الاصطناعي: كل رد من `/chat` يسجّل input/output tokens بجدول
  usage_logs (لو المزوّد يرجّعها). `/admin/analytics/daily` يرجّع بيانات يومية
  (مستخدمين، محادثات، طلبات، توكنز) لآخر N يوم، و`/admin/analytics/export.csv` يصدّرها CSV.
- إشعارات: `/notifications` (عرض/تعليم كمقروء) + `/ws/notifications` (بث فوري عبر
  WebSocket، التوكن كـ query param لأن WebSocket ما يدعم headers مخصصة من المتصفح).
  تنطلق تلقائيًا عند: التسجيل، قفل الحساب، تفعيل/إلغاء الاشتراك (مع إيميل مرافق).
  ملاحظة: البث الفوري بالذاكرة (in-memory) — يشتغل تمام لنسخة واحدة من التطبيق؛ لو صار
  عندك أكتر من نسخة تحتاج Redis pub/sub بدلها.
- الأداء:
  - GZip لضغط الاستجابات الكبيرة تلقائيًا
  - Redis caching على `/billing/plans` و`/admin/stats` (دقيقة واحدة افتراضيًا)
  - إرسال الإيميل بالخلفية عبر Celery+Redis (خدمة `celery_worker` بـ docker-compose) —
    لو Celery/Redis مو مضبوطين، يرجع تلقائيًا للإرسال المباشر بدون ما يكسر التطبيق
  - سياق المحادثة المُرسل لـ AI محدود بآخر 20 رسالة (مو المحادثة كاملة) — أداء وتكلفة أفضل

## النشر: HTTPS، النسخ الاحتياطي، والمراقبة

**HTTPS (Let's Encrypt مجانًا):**
1. عدّل `nginx/nginx.conf`: استبدل placeholder بدومينك بالجزء المعلَّق (تعليمات داخل الملف)
2. شغّل `docker compose up -d nginx` أول (بدون HTTPS بعد)
3. احصل على الشهادة أول مرة:
   ```
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
     -d your-domain.com --email you@example.com --agree-tos --no-eff-email
   ```
4. ألغِ التعليق عن جزء HTTPS بـ nginx.conf وشغّل `docker compose restart nginx`
5. خدمة `certbot` بالـ compose تجدّد الشهادة تلقائيًا كل 12 ساعة (تتأكد بس، ما تجدّد إلا قريب من الانتهاء)

**النسخ الاحتياطي:** خدمة `backup` تاخذ نسخة يومية تلقائيًا لمجلد `./backups` (تحتفظ بآخر 7
أيام). استرجاع يدوي: `docker compose exec -T db sh /scripts/restore.sh /backups/backup_XXX.sql.gz`

**المراقبة:**
- `/health` يتحقق فعليًا من اتصال قاعدة البيانات (مو مجرد رد ثابت) — مناسب لفحوصات
  الصحة عند أي منصة استضافة أو load balancer
- `/metrics` يعرض مقاييس Prometheus (عدد الطلبات، زمن الاستجابة...) لو ثبّت المكتبة

## النشر للإنتاج

راجع الدليل الكامل: [docs/PRODUCTION.md](docs/PRODUCTION.md)

فحص سريع بعد النشر:

```bash
./scripts/smoke.sh https://api.your-domain.com
```
