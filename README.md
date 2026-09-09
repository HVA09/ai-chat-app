# AI Chat SaaS Starter (FastAPI + React)

Thank you for your purchase.

## Folders

- `ai-backend/` — FastAPI API (auth, chat, billing, admin, Docker)
- `ai-frontend/` — React + Vite UI
- `LICENSE.txt` — license terms
- `README.md` — this file

## Quick start

### Backend

```bash
cd ai-backend
cp .env.example .env
# Set: JWT_SECRET_KEY, AI_API_KEY, POSTGRES_PASSWORD, DATABASE_URL, INITIAL_ADMIN_EMAIL
docker compose up --build
```

- API docs (development): http://localhost:8000/docs
- Health: http://localhost:8000/health

### Frontend

```bash
cd ai-frontend
npm install
npm run dev
```

Open http://localhost:5173

The first registered user is **not** automatically an admin. Set `INITIAL_ADMIN_EMAIL` to the intended administrator email before production deployment.

## Production

- `ai-backend/docs/PRODUCTION.md`
- `ai-backend/docs/DEPLOY_BEGINNER_AR.md` (Arabic guide)
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

The patched release no longer exposes FastAPI directly on the public `:8000` port; development traffic on `localhost:8000` goes through Nginx. Refresh tokens are rotated and kept in HttpOnly cookies backed by Redis, and the WebSocket uses the HttpOnly access-token cookie rather than placing JWTs in the URL. Production configuration fails closed for missing secrets/SMTP/admin bootstrap, and upload quotas/streaming are enabled.

For production, set `FRONTEND_URL`, `CORS_ORIGINS`, `INITIAL_ADMIN_EMAIL`, real SMTP/payment settings, and a real HTTPS-enabled Nginx server name/certificate.

Healthcare source configuration is documented in `ai-backend/docs/HEALTHCARE_SOURCES.md`. The app does not expose these sources to the browser automatically; integrate them server-side with rate limits and source attribution.
