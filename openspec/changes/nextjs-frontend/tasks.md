# Implementation Tasks (`nextjs-frontend`)

## Phase 1: FastAPI Backend & OpenSpec Contract (Completed)
- [x] Migrate `app.py`, `src/database/db.py`, `src/auth/security.py`, `src/auth/routes.py`, and `src/routes/*.py` from Flask to FastAPI + Uvicorn + Pydantic (`src/schemas.py`).
- [x] Add `GET /api/auth/session`, `GET /api/health`, rotated `csrf_token` + `user` in `/api/auth/login` and `/api/auth/register`, allowlisted `CORS_ORIGINS`, and `X-Forwarded-For` throttling support.
- [x] Update `requirements.txt`, `Procfile`, and `.env.example` for FastAPI/Uvicorn production deployment.
- [x] Export live OpenAPI 3.1 contract to `openspec/openapi.yaml` and verify all 50 pytest cases pass (`python -m pytest -v`).

## Phase 2: Next.js Project Scaffold & Design System (Completed)
- [x] Scaffold Next.js 15 App Router + TypeScript app in `web/` (`package.json`, `tsconfig.json`, `eslint.config.mjs`).
- [x] Install dependencies: `plotly.js-dist-min`, `@types/plotly.js`, `@netlify/plugin-nextjs`.
- [x] Copy `static/fonts/*.woff2` into `web/public/fonts/` and configure `next/font/local` for `Inter`, `Space Grotesk`, and `JetBrains Mono`.
- [x] Port `static/css/style.css` to `web/src/app/globals.css`, strictly retaining only Obsidian (`#050507`, `#0c0c11`, `#15151c`), Chrome Silver (`#c9cdd3`, `#f2f4f7`, `#8a9098`, `#4d525a`), and Laser Crimson (`#ff1a40`, `#ff4d6d`, `#a10020`).
- [x] Create `web/next.config.mjs` with local dev rewrites (`/api/*`, `/avatar/*` -> `http://127.0.0.1:5000`) and `NEXT_OUTPUT_EXPORT` static export switch (`trailingSlash: true`).

## Phase 3: Core Client Infrastructure & Authentication (Completed)
- [x] Create `web/src/types/api.ts` matching `openspec/openapi.yaml` and `src/schemas.py`.
- [x] Create `web/src/lib/api.ts` (CSRF-sync `apiFetch`) and `web/src/lib/format.ts` (`fmtInr`, `pctf`, `safeNext`).
- [x] Implement `AuthProvider`, `Navbar`, `CommandPalette`, `BgNetwork`, and `ToastProvider` in `web/src/components/` and wire into `web/src/app/layout.tsx` along with `web/src/app/not-found.tsx`.
- [x] Build `/login` and `/register` pages with password toggle and 5-step strength meter.

## Phase 4: Home & Ingestion Flow (Completed)
- [x] Build `/` (`web/src/app/page.tsx`): Hero + animated SVG sparkline card, auth-aware CTA/upload gating, drag-and-drop file uploader (`<=50 MB`), demo buttons (`clean`/`dirty`), and interactive 422 column mapper (`needs_mapping`).

## Phase 5: Analytics Dashboard & Investigation (Completed)
- [x] Create SSR-safe `web/src/components/PlotlyChart.tsx` (`plotly.js-dist-min` via dynamic import + `Plotly.react` + `ResizeObserver`).
- [x] Build `/dashboard`: Filters, Business Pulse, Health Score SVG gauge, 6 KPIs, 7 Plotly charts (`Profit`/`Sales` toggles), linear trend projection, Data Quality report, and `clean.csv` export.
- [x] Build `/investigation`: Question input, preset chips, month comparison selectors, `Auto`/`Profit`/`Sales` switch, 4-tab contributor chart, inside-segment driver cards, findings & anomalies, next checks, report generator, and `contributors.csv` download.

## Phase 6: The Lab, Data Explorer, Reports & Profile (Completed)
- [x] Build `/lab`: Sliders (`commit: false` preview vs `commit: true` release), restore-last-month button, grouped Now vs Scenario chart, monthly goals CRUD with circular pace rings, and private notes CRUD.
- [x] Build `/data`: Searchable, sortable, paginated table (`GET /api/preview`) and cleaned CSV export.
- [x] Build `/reports`: Dataset list, report generation (`POST /api/report/<id>`), and view/download links.
- [x] Build `/profile`: Avatar drag-and-drop upload (`<=3 MB`) & removal, XP/rank/8-badge grid, personal details form, password change form, and delete-account modal.

## Phase 7: Verification & Netlify Deployment
- [x] Update root `netlify.toml` (`base = "web"`, `publish = "out"`) and `web/.env.example`.
- [x] Run backend verification: `python -m pytest -v` (50 passed).
- [x] Run frontend checks: `cd web && npm run typecheck && npm run lint && NEXT_OUTPUT_EXPORT=true npm run build`.
- [ ] Deploy FastAPI backend (`uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`) to Render/Railway, update `netlify.toml` backend URL, and deploy `web/` to Netlify.
