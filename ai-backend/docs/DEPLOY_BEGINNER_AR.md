# دليل النشر للمبتدئ (خطوة بخطوة)

هذا الدليل مكتوب لمن **لا يعرف البرمجة**.  
اتبع الخطوات بالترتيب. لا تتخطّى خطوة.

نوزّع المشروع على جزئين:

| الجزء | ماذا يفعل؟ | أين ننشره؟ (الأسهل) |
|--------|------------|---------------------|
| **Backend** (الخادم) | الحسابات، الشات، الدفع، قاعدة البيانات | سيرفر VPS رخيص |
| **Frontend** (الواجهة) | الصفحات التي يراها المستخدم | Vercel (مجاني للبداية) |

ستحتاج تقريبًا: **ساعة إلى ثلاث ساعات** + بطاقة لدفع السيرفر (حوالي 5–12$/شهر).

---

## قبل أن تبدأ: جهّز هذه الأشياء

### 1) حسابات مجانية / رخيصة

1. **GitHub** → https://github.com  
   لرفع ملفات المشروع.
2. **Vercel** → https://vercel.com  
   انشر الواجهة (سجّل الدخول بـ GitHub).
3. **مزوّد سيرفر** (اختر واحدًا):
   - https://www.digitalocean.com  
   - أو https://www.hetzner.com  
   - أو أي VPS يعطيك Ubuntu
4. **دومين** (اختياري لكن مهم للبيع): من Namecheap / Cloudflare / أي بائع دومين.
5. **مفتاح ذكاء اصطناعي**:
   - OpenAI: https://platform.openai.com/api-keys  
   أو أي مزوّد آخر يدعمه المشروع.

### 2) برامج على جهازك (Windows)

1. ثبّت **Git**: https://git-scm.com/download/win  
2. ثبّت **VS Code** (اختياري): https://code.visualstudio.com  

على Mac: Git غالبًا موجود، أو ثبّته من الموقع.

---

## المرحلة أ — ارفع المشروع على GitHub

### أ-1) أنشئ مستودعين (Repositories)

في GitHub اضغط **New repository** مرتين:

1. اسم الأول: `ai-backend`
2. اسم الثاني: `ai-frontend`

اجعلهما **Private** إن أردت إخفاء الكود.

### أ-2) ارفع الملفات

من مجلد المشروع على جهازك:

**للباك اند:**
```bash
cd ai-backend
git init
git add .
git commit -m "first upload"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-backend.git
git push -u origin main
```

**للفرونت:**
```bash
cd ai-frontend
git init
git add .
git commit -m "first upload"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-frontend.git
git push -u origin main
```

استبدل `YOUR_USERNAME` باسم مستخدمك في GitHub.

> إذا طلب منك تسجيل دخول: استخدم Personal Access Token من إعدادات GitHub وليس كلمة المرور العادية.

---

## المرحلة ب — نشر الواجهة (Frontend) على Vercel

### ب-1) استيراد المشروع

1. ادخل https://vercel.com  
2. **Add New Project**  
3. اختر مستودع `ai-frontend`  
4. اضغط **Deploy**

قد يفشل أول مرة — هذا طبيعي لأننا لم نضع رابط الـ API بعد. نكمّل بعد نشر الباك اند.

### ب-2) ماذا ستحصل؟

Vercel يعطيك رابطًا مثل:

`https://ai-frontend-xxxx.vercel.app`

احفظ هذا الرابط. سنسميه **رابط الفرونت**.

---

## المرحلة ج — إنشاء السيرفر (Backend)

### ج-1) أنشئ Droplet / Server

في DigitalOcean مثلًا:

1. Create → Droplets  
2. اختر **Ubuntu 24.04**  
3. خطة **Basic** بحوالي 6$ (1GB قد تضيق؛ الأفضل 2GB إن أمكن)  
4. Authentication: **Password** (أسهل للمبتدئ) أو SSH Key  
5. Create

سيظهر لك **IP** مثل: `167.99.xx.xx`  
احفظه. سنسميه **IP السيرفر**.

### ج-2) ادخل السيرفر

على Windows: افتح **PowerShell** أو ثبّت **PuTTY**.

```bash
ssh root@IP_السيرفر
```

اكتب كلمة المرور عندما يطلبها (لن تظهر أثناء الكتابة — هذا طبيعي).

### ج-3) ثبّت Docker (انسخ الأوامر كما هي)

بعد الدخول للسيرفر، نفّذ أمرًا أمرًا:

```bash
apt update
apt install -y git curl
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
docker --version
```

إذا ظهر رقم إصدار لـ Docker فأنت بخير.

### ج-4) نزّل مشروع الباك اند على السيرفر

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/ai-backend.git
cd ai-backend
```

### ج-5) أنشئ ملف الأسرار `.env`

```bash
cp .env.example .env
nano .env
```

**nano** محرر نصوص في الطرفية:

- عدّل القيم بالأسهم  
- احفظ: `Ctrl + O` ثم Enter  
- اخرج: `Ctrl + X`

#### قيم مهمة يجب تغييرها

```env
ENVIRONMENT=production
DEBUG=false

POSTGRES_USER=postgres
POSTGRES_PASSWORD=ضع_كلمة_مرور_قوية_هنا
POSTGRES_DB=ai_backend
DATABASE_URL=postgresql://postgres:ضع_كلمة_مرور_قوية_هنا@db:5432/ai_backend

JWT_SECRET_KEY=الصق_هنا_مفتاحا_طويلا
AI_API_KEY=مفتاح_openai_أو_غيره
AI_PROVIDER=openai
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini

FRONTEND_URL=https://ai-frontend-xxxx.vercel.app
CORS_ORIGINS=["https://ai-frontend-xxxx.vercel.app"]
```

ولّد مفتاح JWT من جهازك أو من السيرفر:

```bash
openssl rand -hex 32
```

انسخ الناتج والصقه في `JWT_SECRET_KEY`.

> إذا لم يكن عندك دومين بعد، استخدم رابط Vercel كما فوق.  
> لاحقًا عند شراء دومين تغيّر `FRONTEND_URL` و `CORS_ORIGINS`.

### ج-6) شغّل المشروع

```bash
cd /opt/ai-backend
docker compose up -d --build
```

انتظر حتى ينتهي البناء (قد يأخذ عدة دقائق أول مرة).

تحقق:

```bash
docker compose ps
curl -s http://127.0.0.1:8000/health
```

يجب أن ترى شيئًا فيه `"status":"ok"`.

فحص أوسع:

```bash
./scripts/smoke.sh http://127.0.0.1:8000
```

### ج-7) افتح المنفذ للعالم

الـ API يمر عبر Nginx على المنفذ 80:

في لوحة السيرفر (Firewall) اسمح بـ:

- المنفذ **22** (SSH)
- المنفذ **80** (HTTP)
- المنفذ **443** (HTTPS) لاحقًا

جرّب من متصفحك:

`http://IP_السيرفر/health`

إذا ظهرت JSON فالخادم يعمل.

---

## المرحلة د — اربط الفرونت بالباك اند

### د-1) في Vercel

1. Project → **Settings** → **Environment Variables**  
2. أضف:

| Name | Value |
|------|--------|
| `VITE_API_BASE_URL` | `http://IP_السيرفر` |

(بدون شرطة `/` في النهاية)

3. **Deployments** → آخر نشر → **Redeploy**

### د-2) جرّب الموقع

افتح رابط Vercel:

1. أنشئ حسابًا  
2. سجّل دخولًا  
3. أرسل رسالة في الشات  

إذا ظهر رد من الذكاء الاصطناعي: **نجحت**.

---

## المرحلة هـ — دومين و HTTPS (مهم قبل البيع)

### هـ-1) اشترِ دومينًا

مثال: `myaiapp.com`

### هـ-2) اربط الدومين

في إعدادات DNS عند بائع الدومين:

| النوع | الاسم | القيمة |
|-------|--------|--------|
| A | `api` | IP السيرفر |
| CNAME أو A | `@` أو `www` | حسب تعليمات Vercel |

في Vercel: **Settings → Domains** → أضف `myaiapp.com` واتبع التعليمات.

في السيرفر لاحقًا تستخدم: `https://api.myaiapp.com`

### هـ-3) HTTPS للـ API (ملخص)

اتبع القسم الموجود في `docs/PRODUCTION.md` (Certbot + تعديل nginx).

بعدها حدّث في Vercel:

`VITE_API_BASE_URL=https://api.myaiapp.com`

وفي `.env` على السيرفر:

```env
FRONTEND_URL=https://myaiapp.com
CORS_ORIGINS=["https://myaiapp.com","https://www.myaiapp.com"]
```

ثم:

```bash
docker compose up -d
```

---

## المرحلة و — الدفع (Stripe) بشكل مبسّط

1. افتح https://stripe.com وأنشئ حسابًا  
2. من Dashboard خذ **Secret key** (ابدأ بـ Test mode)  
3. ضعه في `.env`:

```env
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

4. أنشئ Product + Price في Stripe  
5. ضع `price_...` في جدول `plans` في قاعدة البيانات (حقل `stripe_price_id`) — أو اطلب من مطور مساعدتك في هذه النقطة مرة واحدة.

6. Webhook URL:

`https://api.myaiapp.com/billing/webhook/stripe`

---

## إذا توقف شيء — ماذا تفعل؟

### الواجهة تفتح لكن التسجيل يفشل
- تأكد أن `VITE_API_BASE_URL` صحيح  
- تأكد أن `CORS_ORIGINS` يطابق رابط الفرونت حرفيًا  
- من السيرفر: `docker compose logs app --tail=50`

### الشات لا يرد
- تأكد أن `AI_API_KEY` صحيح وفيه رصيد  
- `docker compose logs app --tail=50`

### السيرفر لا يفتح من المتصفح
- الجدار الناري (Firewall)  
- `docker compose ps` — هل nginx و app يعملان؟

### نسيت إعادة تشغيل بعد تعديل `.env`
```bash
cd /opt/ai-backend
docker compose up -d
```

---

## ترتيب النجاح (لخّصه على ورقة)

1. ☐ GitHub: رفع backend + frontend  
2. ☐ Vercel: نشر frontend  
3. ☐ VPS: Ubuntu + Docker  
4. ☐ clone الباك اند + تعديل `.env`  
5. ☐ `docker compose up -d --build`  
6. ☐ `curl /health` ينجح  
7. ☐ Vercel: `VITE_API_BASE_URL` = رابط الـ API  
8. ☐ تجربة تسجيل + شات من المتصفح  
9. ☐ (لاحقًا) دومين + HTTPS  
10. ☐ (لاحقًا) Stripe  

---

## ماذا لا تحتاج أن تفهمه الآن؟

- كيف تعمل قاعدة البيانات من الداخل  
- كيف يُكتب كود Python/React  
- Kubernetes أو أنظمة معقدة  

يكفي أن تنفّذ الأوامر بالترتيب وتراجع الرسائل الحمراء في السجلات.

---

## هل تحتاج مساعدة بشرية مدفوعة؟

إذا علقت عند السيرفر أو DNS، ساعة واحدة مع مستشار تقني (Fiverr / مستقل) غالبًا تكفي لإكمال الربط الأول.  
الكود عندك جاهز؛ المطلوب تشغيل وربط وليس إعادة برمجة.
