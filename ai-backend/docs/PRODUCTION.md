# دليل التشغيل للإنتاج

خطوات عملية لنشر الباك اند بشكل آمن وقابل للصيانة.

## 1) المتطلبات

- سيرفر Linux (2 vCPU / 4GB RAM كحد أدنى مريح)
- Docker + Docker Compose
- دومين يشير لـ IP السيرفر (A record)
- منافذ 80 و 443 مفتوحة

## 2) إعداد الأسرار

```bash
cd /opt/ai-backend   # أو مسار المشروع
cp .env.example .env
chmod 600 .env
```

املأ على الأقل:

| المتغير | ملاحظة |
|---------|--------|
| `ENVIRONMENT=production` | يعطّل DEBUG ويفعّل HSTS |
| `DEBUG=false` | |
| `POSTGRES_PASSWORD` | قوية وعشوائية |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `AI_API_KEY` | مفتاح المزود الحقيقي |
| `AI_PROVIDER` | openai / anthropic / gemini / deepseek |
| `FRONTEND_URL` | https://your-domain.com |
| `CORS_ORIGINS` | `["https://your-domain.com"]` |
| `PAYMENT_PROVIDER` | stripe أو paypal |
| `STRIPE_*` أو `PAYPAL_*` | من لوحة المزود |
| `SMTP_*` | لإيميلات حقيقية (تحقق/إعادة تعيين) |

## 3) التشغيل

```bash
docker compose up -d --build
docker compose ps
curl -sS http://127.0.0.1:8000/health
```

المتوقع من `/health`:

```json
{"status":"ok","database":"ok","environment":"production","app":"AI Backend"}
```

## 4) HTTPS عبر Certbot (ملخص)

1. ضع دومينك في `nginx/nginx.conf` (القسم المعطّل لـ 443).
2. تأكد أن `location /.well-known/acme-challenge/` يعمل على المنفذ 80.
3. احصل على الشهادة:

```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d your-domain.com --email you@example.com --agree-tos --no-eff-email
```

4. ألغِ تعليق كتلة SSL في `nginx.conf` وأعد تشغيل nginx:

```bash
docker compose restart nginx
```

## 5) Webhooks الدفع

- **Stripe:** أضف endpoint  
  `https://api.your-domain.com/billing/webhook/stripe`  
  واحفظ `STRIPE_WEBHOOK_SECRET`.
- **PayPal:** سجّل webhook للأحداث `BILLING.SUBSCRIPTION.*`  
  واحفظ `PAYPAL_WEBHOOK_ID`.

## 6) النسخ الاحتياطي

`docker-compose` يشغّل خدمة `backup` يوميًا (مجلد `./backups`).

الاستعادة لازم تصير **داخل حاوية `db`** (فيها `psql` وتشوف `$DATABASE_URL` من `.env`)،
مو بتشغيل السكربت مباشرة على السيرفر:

```bash
docker compose exec -T db sh /scripts/restore.sh /backups/backup_XXXXXXXX_XXXXXX.sql.gz
```

## 7) المراقبة السريعة

| فحص | أمر |
|-----|-----|
| صحة التطبيق | `curl /health` |
| المقاييس | `curl /metrics` |
| السجلات | `docker compose logs -f app nginx` |

## 8) Smoke test بعد كل نشر

```bash
./scripts/smoke.sh https://api.your-domain.com
```

يفحص `/health` و `/billing/plans`.

## 9) قائمة تحقق قبل إطلاق عام

- [ ] `DEBUG=false` و `ENVIRONMENT=production`
- [ ] CORS مضبوط على دومين الفرونت فقط
- [ ] JWT وكلمات مرور DB قوية
- [ ] SMTP يعمل (رسالة تجريبية)
- [ ] Stripe/PayPal webhook مضبوط
- [ ] HTTPS صالح
- [ ] نسخة احتياطية واستعادة مجرّبة مرة واحدة
- [ ] Privacy + Terms منشورتان على الفرونت
