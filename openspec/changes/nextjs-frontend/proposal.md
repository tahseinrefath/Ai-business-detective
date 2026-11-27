# Change Proposal: Migrate Frontend to Next.js on Netlify (`nextjs-frontend`)

- **Change ID**: `nextjs-frontend`
- **Status**: Backend Ready (FastAPI) · Next.js Frontend Implemented (`web/`)
- **Target Stack**: Next.js (App Router + TypeScript) on Netlify + FastAPI (Python) on Render/Railway

## Why
1. The existing UI spans Jinja2 templates (`templates/*.html`) and generated vanilla JS (`frontend/` via `scripts/build_frontend.py`), duplicating page shells and relying on manual `innerHTML` string templates.
2. Migrating the frontend to **Next.js App Router + TypeScript** provides modular React components, compile-time contract safety against FastAPI's OpenAPI 3.1 schema (`openspec/openapi.yaml`), cleaner state/filter synchronization, and first-class Netlify deployment.
3. Retaining **FastAPI + Pandas + scikit-learn** on the backend keeps all data-cleaning, file-parsing (`.xlsx`, `.ods`, `.pdf`, `.pbix`, `.csv`, `.json`), and ML anomaly detection deterministic and tested.

## What Changes

### Completed on FastAPI Backend
- Migrated `app.py`, `src/database/db.py`, `src/auth/security.py`, `src/auth/routes.py`, and all `src/routes/*.py` blueprints from Flask to **FastAPI** (`APIRouter` + Starlette `SessionMiddleware` + Pydantic `src/schemas.py`).
- Added `GET /api/auth/session` (public session + CSRF bootstrap), `GET /api/health`, and rotated `csrf_token` + `user` responses on `POST /api/auth/login` and `POST /api/auth/register`.
- Added allowlisted `CORS_ORIGINS` + `Vary: Origin`, `OPTIONS` preflight support, `X-Forwarded-For` IP resolution in `LoginThrottle`, and `uvicorn` production `Procfile`.
- Exported verified OpenAPI 3.1 spec to `openspec/openapi.yaml` (27 API paths).

### Planned for Next.js Frontend (`web/`)
- Scaffolded Next.js App Router + TypeScript app in `web/` with `plotly.js-dist-min` client-only rendering (`PlotlyChart.tsx`).
- Implement shared layout (`Navbar`, `CommandPalette`, `BgNetwork`, `ToastProvider`, `AuthProvider`) using self-hosted `next/font/local` fonts and the strict Obsidian · Chrome · Laser CSS tokens.
- Implement all 8 authenticated/public routes (`/`, `/login`, `/register`, `/dashboard`, `/investigation`, `/lab`, `/data`, `/reports`, `/profile`) plus `/404`.
- Configure `next.config.mjs` (local dev rewrites to `http://127.0.0.1:5000` + optional `output: "export"`) and `netlify.toml` (Netlify proxy rewrites `/api/*` and `/avatar/*` -> FastAPI backend URL).

## Capabilities
- `auth-profile`: Session hydration, CSRF rotation sync, login/register/logout, lock-out handling, avatar upload/crop, profile edits, password change, gamification XP/ranks/badges, account deletion.
- `dataset-ingestion`: 50 MB multi-format upload, synthetic demo cases (`clean`/`dirty`), interactive 422 column mapping (`needs_mapping`), per-user active dataset persistence.
- `analytics-dashboard`: Multi-dimension filters, business pulse, transparent 0-100 health gauge, 6 KPIs, 7 SSR-safe Plotly charts, linear next-month projection, data quality audit, `clean.csv` export.
- `investigation-ai`: Plain-English Q&A, period comparison picker, Auto/Profit/Sales switch, 4 contributor dimensions, driver breakdown, findings & unusual days (`IsolationForest` + robust z-score), next checks, report generation, `contributors.csv` export.
- `whatif-goals-notes`: Single-segment sensitivity sliders (`commit: false` preview vs `commit: true` XP award), restore-last-month shortcut, monthly goals CRUD with daily pace rings, private case notes CRUD.
- `explorer-reports-palette`: Searchable/sortable/paginated data explorer (`/data`), HTML report manager (`/reports`), and global `Ctrl+K` / `Cmd+K` command palette.

## Non-Goals
- Porting Pandas, scikit-learn, `pdfplumber`, or `pbixray` to Node.js.
- Introducing third-party UI libraries that violate the Obsidian/Chrome/Laser palette or add theme switchers.
