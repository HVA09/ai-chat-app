# AI Chat SaaS Starter (FastAPI + React)

FastAPI + React/Vite AI chat SaaS starter with authentication, chat, billing, admin features, file uploads, notifications, Docker, and multiple AI providers.

## Folders

- `ai-backend/` — FastAPI API
- `ai-frontend/` — React + Vite UI
- `.github/workflows/ci.yml` — CI for backend and frontend

## Quick start

### Backend

```bash
cd ai-backend
cp .env.example .env
# Fill in JWT_SECRET_KEY, AI_API_KEY, database, Redis, SMTP, and payment settings as needed.
docker compose up --build
```

Development API is available through Nginx at `http://localhost:8000`.

### Frontend

```bash
cd ai-frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Security hardening included

- FastAPI is not directly published as a host port; development traffic goes through Nginx.
- Access and refresh authentication use HttpOnly cookies; refresh tokens are rotated and tracked in Redis.
- WebSocket authentication does not place JWTs in the URL.
- Production settings fail closed for missing core secrets/configuration.
- Uploads are streamed in chunks and protected by per-user count/storage quotas.
- Billing checkout URLs are server-controlled instead of client-supplied.
- Production hides FastAPI docs/OpenAPI endpoints.
- CI runs backend compilation/tests and frontend tests/build.

See `ai-backend/docs/PRODUCTION.md` and `ai-backend/docs/HEALTHCARE_SOURCES.md` before deployment.

## Important

Do not commit `.env`, API keys, passwords, certificates, or other secrets.
