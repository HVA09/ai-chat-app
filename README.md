# AI Chat SaaS Starter (FastAPI + React)

Thank you for your purchase.

## Folders

- `ai-backend/` — FastAPI API (auth, chat, billing, admin, Docker)
- `ai-frontend/` — React + Vite UI
- `LICENSE.txt` — license terms
- `README.md` — this file

## Quick start

### Backend — development

```bash
cd ai-backend
cp .env.example .env
# Set: JWT_SECRET_KEY, AI_API_KEY, POSTGRES_PASSWORD, DATABASE_URL, INITIAL_ADMIN_EMAIL
docker compose -f docker-compose.dev.yml up --build
```

- API: http://localhost:8000
- API docs (development): http://localhost:8000/docs
- Health: http://localhost:8000/health

The development Compose file intentionally publishes FastAPI on `localhost:8000`. Do not use this configuration as the public production deployment.

### Frontend

```bash
cd ai-frontend
npm install
npm run dev
```

Open http://localhost:5173

The first registered user is **not** automatically an admin. Set `INITIAL_ADMIN_EMAIL` to the intended administrator email before production deployment.

## Production

Use the dedicated production Compose file instead of the development configuration:

```bash
cd ai-backend
cp .env.production.example .env.production
# Fill every production secret, domain, SMTP/payment setting, CORS origin, and BACKEND_IMAGE
docker compose -f docker-compose.prod.yml up -d
```

Production publishes only Nginx on ports `80` and `443`; FastAPI is internal to the Compose network. The production file uses a prebuilt `BACKEND_IMAGE` so deployment can pull an application image rather than building source code on the server.

### HTTPS setup

HTTPS must use a real domain and a valid certificate. Do **not** enable the certificate template with placeholder values.

1. Point your DNS `A/AAAA` record at the production server.
2. Copy `ai-backend/nginx/nginx.production.example.conf` over `ai-backend/nginx/nginx.conf` and replace every `your-domain.com` with the real domain.
3. Start Nginx and Certbot with the production Compose file so the ACME webroot is available.
4. Obtain the certificate for the real domain using Certbot's webroot challenge.
5. Validate the Nginx configuration with `docker compose -f docker-compose.prod.yml exec nginx nginx -t`.
6. Restart Nginx and verify `https://YOUR_DOMAIN/health`.
7. Keep HTTP-to-HTTPS redirect enabled after HTTPS has been verified.

The repository's active `nginx.conf` intentionally remains HTTP-only until the real domain/certificate are supplied. The production template includes TLS 1.2/1.3, HSTS, security headers, WebSocket proxying, rate limits, and the health endpoint.

See:

- `ai-backend/docs/PRODUCTION.md`
- `ai-backend/docs/DEPLOY_BEGINNER_AR.md` (Arabic guide)
- `ai-backend/nginx/nginx.production.example.conf`
- Smoke: `cd ai-backend && ./scripts/smoke.sh https://your-api.com`

Frontend: copy `ai-frontend/.env.production.example` to `.env.production` and set `VITE_API_BASE_URL`.

## You need

- Your own AI API key
- Hosting (VPS + Docker for API; Vercel OK for UI)
- Your Stripe/PayPal keys for payments
- SMTP for real emails (optional in dev)

## License

See `LICENSE.txt`. Commercial end-products allowed. Do not resell this template as-is.

## Security hardening included

The patched release no longer exposes FastAPI publicly in the production Compose configuration. Development uses a separate Compose file with a localhost-only `:8000` mapping. Refresh tokens are rotated and kept in HttpOnly cookies backed by Redis, and the WebSocket uses the HttpOnly access-token cookie rather than placing JWTs in the URL. Production configuration fails closed for missing secrets/SMTP/admin bootstrap, and upload quotas/streaming are enabled.

Nginx now has a dedicated health route and baseline security headers. The HTTPS configuration is deliberately template-based until a real domain and certificate exist.

For production, set `FRONTEND_URL`, `CORS_ORIGINS`, `INITIAL_ADMIN_EMAIL`, real SMTP/payment settings, a real HTTPS-enabled Nginx server name/certificate, and `BACKEND_IMAGE`.

Healthcare source configuration is documented in `ai-backend/docs/HEALTHCARE_SOURCES.md`. The app does not expose these sources to the browser automatically; integrate them server-side with rate limits and source attribution.
