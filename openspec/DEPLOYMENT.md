# Deployment Guide — AI Business Detective

## Architecture Overview

```
Browser → Netlify CDN (Next.js static export)
              ↓  /api/* proxy
         Render.com (FastAPI + Uvicorn)
              ↓
         SQLite (persistent volume)
              ↓
         Google Gemini 1.5 Flash API
```

---

## Backend — Render.com

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `SECRET_KEY` | 32+ char random string for CSRF/session | ✅ |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | ✅ |
| `DATABASE_PATH` | SQLite file path (use persistent disk) | ✅ |
| `PORT` | Set by Render automatically | auto |

### Deploy Steps

1. Connect GitHub repo to Render
2. Set **Build Command:** `pip install -r requirements.txt`
3. Set **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
4. Attach a **Persistent Disk** at `/data` and set `DATABASE_PATH=/data/abd.db`
5. Add all environment variables above
6. Deploy — health check at `GET /api/health`

---

## Frontend — Netlify

### Environment Variables

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | Full URL of Render backend (for server-side proxy) |
| `NEXT_PUBLIC_API_BASE_URL` | Same URL (exposed to browser) |

### Deploy Steps

1. Connect GitHub repo to Netlify
2. Base directory: `web`
3. Build command: `npm run build` (uses `NEXT_OUTPUT_EXPORT=true` from `netlify.toml`)
4. Publish directory: `out`
5. Add environment variables
6. Deploy

> **Note:** `netlify.toml` already configures the `/api/*` → backend proxy and security headers.

---

## Branches → Environments

| Branch | Environment | URL pattern |
|--------|-------------|-------------|
| `dev` | Development | `dev--abd.netlify.app` |
| `uat` | Staging / UAT | `uat--abd.netlify.app` |
| `prod` | Pre-production | `prod--abd.netlify.app` |
| `main` | Production | `ai-business-detective.netlify.app` |

Netlify auto-deploys branch previews for each push.

---

## CI Checklist (before merging to main)

- [ ] `python -m pytest -v` → 50 passed
- [ ] `cd web && npm run typecheck` → 0 errors
- [ ] `cd web && npm run lint` → 0 warnings
- [ ] `NEXT_OUTPUT_EXPORT=true npm run build` → 0 errors
- [ ] Manual smoke test on UAT environment
- [ ] `GET /api/health` returns `{"status":"ok"}`
