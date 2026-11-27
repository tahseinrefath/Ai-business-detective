# OpenSpec: Next.js Frontend Migration & Netlify Deployment (`migrate-frontend-to-nextjs`)

> **Format:** Consolidated OpenSpec Overview (mirrors the modular OpenSpec tree in [`openspec/`](openspec/project.md))  
> **Modular OpenSpec Files:**
> - [`openspec/project.md`](openspec/project.md) — Project context, design rules & verification
> - [`openspec/openapi.yaml`](openspec/openapi.yaml) — Live-exported FastAPI OpenAPI 3.1 contract (27 routes)
> - [`openspec/changes/nextjs-frontend/proposal.md`](openspec/changes/nextjs-frontend/proposal.md) — Change proposal
> - [`openspec/changes/nextjs-frontend/design.md`](openspec/changes/nextjs-frontend/design.md) — Architecture, Netlify proxy, CSRF sync & starter code
> - [`openspec/changes/nextjs-frontend/specs/`](openspec/changes/nextjs-frontend/specs/auth-profile/spec.md) — 6 capability spec files (`auth-profile`, `dataset-ingestion`, `analytics-dashboard`, `investigation-ai`, `whatif-goals-notes`, `explorer-reports-palette`)
> - [`openspec/changes/nextjs-frontend/tasks.md`](openspec/changes/nextjs-frontend/tasks.md) — Ordered implementation checklist
>
> **Target Repository:** `Ai-business-detective`  
> **Change ID:** `nextjs-frontend`  
> **Status:** Backend Ready (FastAPI) · Frontend Ready to Implement  

---

## 1. Proposal

### 1.1 Why
The current frontend in `templates/` (Jinja2) and `frontend/` (generated static HTML/vanilla JS) duplicates layout/UI logic across HTML shells, relies on manual DOM string concatenation, and lacks component-level TypeScript type safety. Migrating the frontend to **Next.js (App Router + TypeScript)** provides:
- Shared layout, typed API contracts aligned with FastAPI's `/openapi.json` (`src/schemas.py`), and modular React components for all 8 views.
- Seamless deployment to **Netlify** while keeping the **Python/FastAPI + Pandas + scikit-learn** analytics backend intact.
- Strict preservation of the **Obsidian · Chrome · Laser** design system, offline WOFF2 typography, and deterministic analytics guardrails.

### 1.2 What Changes
- **Added**: A dedicated Next.js App Router frontend application (`web/` or `frontend-next/`) with TypeScript, Plotly (`react-plotly.js` / `plotly.js-dist-min` loaded client-only via `next/dynamic`), and Netlify deployment config (`netlify.toml`).
- **Completed on Python Backend (migrated from Flask to FastAPI)**:
  - `app.py`: FastAPI application factory (`create_app()` + `app`), `SessionMiddleware`, exception handlers preserving `{"error": "..."}` payloads, static mount `/static`, `/docs`, `/redoc`, and `/openapi.json`.
  - `src/schemas.py`: Typed Pydantic v2 request/response schemas (`RegisterRequest`, `LoginRequest`, `AskRequest`, `WhatIfRequest`, etc.).
  - `src/auth/routes.py` & `src/routes/*.py`: Converted to FastAPI `APIRouter` modules with `Depends(require_user)`, `GET /api/auth/session`, `GET /api/health`, and `csrf_token` + `user` returned directly from `POST /api/auth/login` and `POST /api/auth/register`.
  - `src/auth/security.py` & `src/database/db.py`: Per-request SQLite/avatar `ContextVar` isolation, allowlisted `CORS_ORIGINS` with `Vary: Origin`, `OPTIONS` preflight support, `X-Forwarded-For` proxy IP handling, and `/api/health` + `/api/auth/session` + `/docs` + `/openapi.json` in `PUBLIC_PATHS`.
  - `Procfile` & `requirements.txt`: Configured for `uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`.
- **Unchanged**: All analytics engines (`src/analytics/*`), data cleaning/loading (`src/data_processing/*`), AI explainer (`src/ai/*`), SQLite/PostgreSQL schema (`src/database/repository.py`), and all 50 backend pytest cases (`tests/`).

### 1.3 Non-Goals
- Rewriting Pandas, scikit-learn `IsolationForest`, or file parsers (`openpyxl`, `pdfplumber`, `pbixray`) in JavaScript/Node.js. All computation remains in Python.
- Changing the three-color palette or adding theme/accent switchers (prohibited by `tests/test_palette.py`).
- Allowing unverified causal claims in UI copy (must always state contributors show *where* a change happened, not proof of *why*).

---

## 2. Design & Architecture Decisions

### 2.1 Deployment Topology (Netlify + Python FastAPI Backend)
- **Primary (Recommended) — Netlify Reverse Proxy (`output: "export"` or `@netlify/plugin-nextjs`)**:
  - Frontend deployed to Netlify (`https://<site>.netlify.app`).
  - Backend FastAPI service deployed to Render / Railway / Fly.io (`https://<api>.onrender.com`) via `Procfile` (`uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`).
  - Netlify proxies `/api/*` and `/avatar/*` to the FastAPI backend with HTTP `200` rewrite (`force = true`).
  - Because requests stay same-origin from the browser's perspective, Starlette `SessionMiddleware`'s `HttpOnly`, `SameSite=Lax` session cookie and `X-CSRF-Token` validation work without third-party cookie blocking.
- **Local Development**:
  - FastAPI runs on `http://127.0.0.1:5000` (`python app.py` or `uvicorn app:app --reload --port 5000`; interactive OpenAPI UI at `http://127.0.0.1:5000/docs`).
  - Next.js dev server runs on `http://localhost:3000`.
  - `next.config.mjs` defines `rewrites()` forwarding `/api/:path*` and `/avatar/:path*` to `http://127.0.0.1:5000` (so `localhost:3000` also stays same-origin).
- **Direct Cross-Origin Fallback**:
  - If `NEXT_PUBLIC_API_BASE_URL` is explicitly set (no proxy), FastAPI returns allowlisted `Access-Control-Allow-Origin` + `Access-Control-Allow-Credentials: true`, and production backend sets `SESSION_COOKIE_SAMESITE=None` and `SESSION_COOKIE_SECURE=True`.

### 2.2 CSRF Token Synchronization in a Next.js SPA
- FastAPI's `log_in(request, user_id)` calls `request.session.clear()` and generates a **new** `request.session["csrf"]` on login/register (`src/auth/security.py`).
- In a Next.js SPA using client-side navigation (`router.push`), full page reloads do not happen, so an in-memory CSRF token from before login would cause `403 Security check failed` on the next mutation.
- **Solution**:
  1. On app mount (`AuthProvider`), call `GET /api/auth/session` with `credentials: 'include'` to obtain initial `{ csrf_token, authenticated, user, stats }`.
  2. Every JSON response from `apiFetch()` inspects `data.csrf_token` and updates the in-memory CSRF token immediately (`POST /api/auth/login` and `POST /api/auth/register` both return the rotated `csrf_token` and `user`).
  3. Every mutating request (`POST`, `PUT`, `PATCH`, `DELETE`) attaches `X-CSRF-Token`.

### 2.3 Design System & Guardrails
- **Strict 3-Family Palette** (verified against `tests/test_palette.py`):
  - **Obsidian Black** (`max(R,G,B) <= 64`): `--obsidian: #050507`, `--obsidian2: #0c0c11`, `--obsidian3: #15151c`
  - **Chrome Silver** (`max - min <= 16`): `--silver: #c9cdd3`, `--silver-hi: #f2f4f7`, `--silver-lo: #8a9098`, `--silver-dim: #4d525a`
  - **Laser Crimson** (`R >= 140, G <= 100, B <= 120, R - G >= 90`): `--crimson: #ff1a40`, `--crimson-hi: #ff4d6d`, `--crimson-lo: #a10020`
  - **Semantic Mapping**: Good/increase = `#f2f4f7` (silver-hi); Bad/decline/alerts/primary action = `#ff1a40` / `#ff4d6d` (crimson); No theme/accent toggle (`data-accent` / `setAccent` forbidden).
- **Typography**: Self-hosted WOFF2 via `next/font/local` pointing to `Inter`, `Space Grotesk`, and `JetBrains Mono` (copied from `static/fonts/`).
- **Monochrome Emojis**: Keep `font-variant-emoji: text` on `body` and append `\uFE0E` to pictographic text where appropriate.
- **Plotly SSR Safety**: `plotly.js` references `window`/`self` at module evaluation time. Always render charts in a `'use client'` wrapper loaded with `dynamic(() => import('@/components/PlotlyChart'), { ssr: false })`.
- **XSS Safety**: Render user-controlled text (`notes`, `filename`, `name`, `job_title`, `company`, `location`, `bio`) purely via React JSX interpolation (never `dangerouslySetInnerHTML`).

---

## 3. Normative Specifications (OpenSpec Capabilities)

### 3.1 Capability: Authentication, Session Hydration & Profile (`auth-profile`)

#### Requirement: Session Hydration & Route Protection
The Next.js app SHALL hydrate session state on initial mount via `GET /api/auth/session` and protect authenticated routes (`/dashboard`, `/investigation`, `/lab`, `/data`, `/reports`, `/profile`).

- **#### Scenario: Unauthenticated user visits a protected route**
  - **WHEN** `GET /api/auth/session` returns `{ authenticated: false, csrf_token: "..." }`
  - **AND** the user visits `/dashboard`, `/investigation`, `/lab`, `/data`, `/reports`, or `/profile`
  - **THEN** the app SHALL redirect to `/login?next=<encoded_path_and_query>`.

- **#### Scenario: User signs in or registers with valid credentials**
  - **WHEN** the user submits `/login` or `/register`
  - **THEN** the client sends `POST /api/auth/login` or `POST /api/auth/register` with `X-CSRF-Token` and `credentials: 'include'`
  - **AND** on `200 OK`, stores the rotated `csrf_token` and `user` in `AuthContext` and navigates to `safeNext(r.next || '/dashboard')` (rejecting protocol-relative `//` or external URLs).

- **#### Scenario: Login lock-out after repeated failures**
  - **WHEN** 5 invalid password attempts occur for an email+IP within 300 seconds
  - **THEN** the API returns `429` with `"Too many failed attempts. Try again in X minute(s)."` and the form displays the alert banner.

- **#### Scenario: Profile management, avatar upload, and account deletion**
  - **WHEN** an authenticated user edits profile details (`PUT /api/profile`), changes password (`POST /api/profile/password`), uploads/deletes an avatar (`POST /api/profile/avatar`, `DELETE /api/profile/avatar`, max 3 MB PNG/JPG/WEBP/GIF), or confirms account deletion (`POST /api/profile/delete`)
  - **THEN** profile stats (`xp`, `level`, `title`, `xp_into_level`, `xp_per_level`, 8 `badges`) update dynamically, and account deletion clears all `abd_dataset*` localStorage keys and redirects to `/`.

---

### 3.2 Capability: Data Ingestion & Column Mapping (`dataset-ingestion`)

#### Requirement: File Upload, Demo Cases & Interactive Column Mapping
Authenticated users SHALL be able to upload spreadsheets/documents up to 50 MB or load synthetic demo datasets, with an interactive fallback mapper when column headers are unrecognized.

- **#### Scenario: Load demo dataset**
  - **WHEN** an authenticated user clicks **Open the demo case** (`kind: "clean"`) or **See it fix messy data** (`kind: "dirty"`) on `/` (or triggers it from `Ctrl+K`)
  - **THEN** `POST /api/sample` returns `{ dataset, months, source_note }`, saves `dataset.id` and `dataset.filename` under per-user key `abd_dataset_<uid>` in `localStorage`, and shows links to `/dashboard` and `/investigation`.

- **#### Scenario: Upload with unrecognized column headers (HTTP 422)**
  - **WHEN** `POST /api/upload` (multipart `file` accepting `.csv,.tsv,.txt,.xlsx,.xlsm,.xls,.ods,.json,.pdf,.pbix`) returns `422` with `needs_mapping: true`
  - **THEN** the UI renders the 5-row preview table and role selectors (`order_date*`, `sales*`, `profit`, `product`, `category`, `region`, `quantity`, `discount_pct`) pre-populated from `suggestions`
  - **AND** submitting sends `POST /api/upload/map` with `{ token, filename, mapping }`, enforcing that `order_date` and `sales` are selected and no source column is assigned twice.

---

### 3.3 Capability: Performance Dashboard (`analytics-dashboard`)

#### Requirement: Filtered KPIs, Health Score, Charts & Data Quality
The `/dashboard` page SHALL display real-time filtered KPIs, business pulse cards, a 0-100 health score gauge, 7 interactive Plotly visualizations + trend projection, and the data quality audit.

- **#### Scenario: Filter changes reload dashboard metrics**
  - **WHEN** the user changes `region`, `category`, `product`, `start`, or `end` (or clicks Reset)
  - **THEN** the client requests `GET /api/dashboard?dataset=<id>&...`
  - **AND** updates the 6 KPI cards (`total_sales`, `total_profit`, `profit_margin`, `total_orders`, `units_sold`, `avg_order_value`), Business Pulse strip, Health Score SVG ring + 4 breakdown bars (`Growth`, `Profitability`, `Stability`, `Data quality`), Plotly charts (`cMonthly`, `cDaily`, `cProducts`, `cRegions`, `cHeat`, `cCat`, and `cDisc` when `discount_bands != null`), next-month linear projection card (or message if `< 3` months), and Data Quality report.
  - **AND** if `422` is returned (no rows match filters), displays the error toast without clearing filter controls.

---

### 3.4 Capability: Case Investigation (`investigation-ai`)

#### Requirement: Natural-Language / Period Investigation & Evidence Display
The `/investigation` page SHALL allow asking plain-English questions, selecting two periods (`previous` -> `current`) and metric (`auto` | `profit` | `sales`), and inspecting calculated evidence.

- **#### Scenario: Run investigation**
  - **WHEN** the user submits a question (max 300 chars), clicks a preset chip, changes period dropdowns, or switches metric segment
  - **THEN** `POST /api/ask` returns `{ investigation, findings, next_checks, explanation, question }`
  - **AND** displays the verdict percentage change, rule/LLM badge (`explanation.source`), plain-English explanation, `partial_warning` banner (when present), contributor bar chart switchable across 4 tabs (`segment`, `product`, `region`, `category`), inside-segment driver breakdown (`orders`, `units`, `avg_selling_price`, `margin`, `avg_discount`), key findings list, unusual days (`anomalies`), recommended `next_checks`, **Generate report** action (`POST /api/report/<id>`), and **Contributors CSV** export link (`/api/export/<id>/contributors.csv`).

---

### 3.5 Capability: What-If Lab, Monthly Goals & Case Notes (`whatif-goals-notes`)

#### Requirement: Sensitivity Simulator, Goals Tracking & Private Notes
The `/lab` page SHALL provide a single-segment sensitivity simulator, monthly goal progress rings, and per-dataset case notes.

- **#### Scenario: What-if slider drag vs release**
  - **WHEN** the user drags `Orders` (`-80%`..`+100%`), `Average price per order` (`-30%`..`+30%`), or `Profit margin` (`-15`..`+15` pts) sliders (or clicks **Match last month's orders**)
  - **THEN** debounced `input` changes call `POST /api/whatif` with `commit: false` (preview only, no XP awarded) and update the grouped Now vs Scenario bar chart
  - **AND** slider `change` (release), segment selection, or restore button calls `POST /api/whatif` with `commit: true` (awarding `whatif` XP).

- **#### Scenario: Goals & Notes CRUD**
  - **WHEN** the user creates/updates a goal (`PUT /api/goals` with `metric: 'sales'|'profit'`, `amount > 0`), deletes a goal (`DELETE /api/goals`), adds a note (`POST /api/notes`, 1-500 chars, max 100 per dataset), or deletes a note (`DELETE /api/notes/<id>`)
  - **THEN** the UI immediately refreshes goals (`GET /api/goals`) with daily pace rings or notes (`GET /api/notes`) with safe escaped rendering.

---

### 3.6 Capability: Data Explorer, Reports & Command Palette (`explorer-reports-palette`)

#### Requirement: Paginated Data Explorer, Reports Console & Ctrl+K Palette
- `/data`: Searchable (`q` debounced 250ms), sortable (`order_date`, `product`, `category`, `region`, `quantity`, `sales`, `profit`, `discount_pct`), paginated (`size=15`) table via `GET /api/preview` plus `/api/export/<id>/clean.csv` download.
- `/reports`: Lists all user datasets via `GET /api/datasets`, checks existing reports via `GET /api/report/<id>`, generates via `POST /api/report/<id>`, and opens or downloads (`?download=1`) the self-contained HTML report.
- Global `Ctrl+K` / `Cmd+K` Command Palette: Keyboard-navigable (`ArrowUp`, `ArrowDown`, `Enter`, `Escape`) quick actions adapting to `authenticated` state.

---

## 4. Verified Backend API Contract

All routes live in `src/auth/routes.py` and `src/routes/*.py`. Every mutating method (`POST`, `PUT`, `PATCH`, `DELETE`) requires `X-CSRF-Token` matching the session cookie.

| Method & Path | Auth | Request Payload / Query | Success Response | Error Codes |
|---|---|---|---|---|
| `GET /api/health` | Public | — | `200 { status: "ok" }` | — |
| `GET /api/auth/session` | Public | — | `200 { csrf_token, authenticated, user, stats }` | — |
| `POST /api/auth/register` | Public + CSRF | `{ name, email, password, next? }` | `200 { ok, next, csrf_token, user }` | `403, 409, 422` |
| `POST /api/auth/login` | Public + CSRF | `{ email, password, next? }` | `200 { ok, next, csrf_token, user }` | `401, 403, 429` |
| `POST /api/auth/logout` | Auth + CSRF | — | `200 { ok: true }` | `401, 403` |
| `GET /api/profile` | Auth | — | `200 { user, stats }` | `401` |
| `PUT /api/profile` | Auth + CSRF | `{ name, job_title, company, location, bio }` | `200 { ok: true, user }` | `401, 403, 422` |
| `POST /api/profile/password` | Auth + CSRF | `{ current, new }` | `200 { ok: true }` | `401, 403, 422` |
| `POST /api/profile/avatar` | Auth + CSRF | `FormData(avatar)` | `200 { ok: true, user }` | `400, 401, 403, 422` |
| `DELETE /api/profile/avatar` | Auth + CSRF | — | `200 { ok: true, user }` | `401, 403` |
| `GET /avatar/me` | Auth | `?v=<ts>` | `200 image/png` | `401, 404` |
| `POST /api/profile/delete` | Auth + CSRF | `{ password }` | `200 { ok: true }` | `401, 403` |
| `POST /api/upload` | Auth + CSRF | `FormData(file)` (<=50 MB) | `200 { dataset, months, source_note }` | `400, 401, 403, 413, 422` |
| `POST /api/upload/map` | Auth + CSRF | `{ token, filename?, mapping }` | `200 { dataset, months, source_note }` | `400, 401, 403, 404, 422` |
| `POST /api/sample` | Auth + CSRF | `{ kind: "clean" \| "dirty" }` | `200 { dataset, months, source_note }` | `400, 401, 403, 422` |
| `GET /api/datasets` | Auth | — | `200 DatasetMeta[]` | `401` |
| `GET /api/dashboard` | Auth | `?dataset=&region=&category=&product=&start=&end=` | `200 DashboardResponse` | `401, 404, 422` |
| `GET /api/options` | Auth | `?dataset=` | `200 FilterOptions` | `401, 404` |
| `GET /api/preview` | Auth | `?dataset=&q=&sort=&dir=&page=&size=` | `200 PreviewResponse` | `401, 404` |
| `GET /api/export/:id/clean.csv` | Auth | — | `200 text/csv` | `401, 404` |
| `GET /api/export/:id/contributors.csv` | Auth | `?metric=&previous=&current=` | `200 text/csv` | `401, 404, 422` |
| `POST /api/investigate` | Auth + CSRF | `{ dataset, metric?, previous?, current? }` | `200 InvestigationResponse` | `401, 403, 404, 422` |
| `POST /api/ask` | Auth + CSRF | `{ dataset, question, metric?, previous?, current? }` | `200 InvestigationResponse` | `400, 401, 403, 404, 422` |
| `GET /api/goals` | Auth | `?dataset=` | `200 GoalsResponse` | `401, 404` |
| `PUT /api/goals` | Auth + CSRF | `{ dataset, metric, amount }` | `200 { ok: true }` | `401, 403, 404, 422` |
| `DELETE /api/goals` | Auth + CSRF | `{ dataset, metric }` (or `?dataset=&metric=`) | `200 { ok: true }` | `401, 403, 404` |
| `GET /api/notes` | Auth | `?dataset=` | `200 { notes }` | `401, 404` |
| `POST /api/notes` | Auth + CSRF | `{ dataset, text }` | `201 { ok: true }` | `401, 403, 404, 422` |
| `DELETE /api/notes/:id` | Auth + CSRF | — | `200 { ok: true }` | `401, 403, 404` |
| `GET /api/whatif/segments` | Auth | `?dataset=` | `200 { current, previous, segments }` | `401, 404` |
| `POST /api/whatif` | Auth + CSRF | `{ dataset, segment, commit?, order_change_pct, price_change_pct, margin_change_pts }` | `200 WhatIfResponse` | `401, 403, 404, 422` |
| `POST /api/report/:id` | Auth + CSRF | `{ metric?, previous?, current? }` | `200 { ok: true, url }` | `401, 403, 404, 422` |
| `GET /api/report/:id` | Auth | `?download=1` | `200 text/html` | `401, 404` |

---

## 5. Corrected Next.js Foundation Code

### 5.1 Proposed Next.js Directory Layout (`web/`)

```text
web/
├── public/
│   └── fonts/
│       ├── inter-latin-wght-normal.woff2
│       ├── space-grotesk-latin-wght-normal.woff2
│       └── jetbrains-mono-latin-wght-normal.woff2
├── src/
│   ├── app/
│   │   ├── layout.tsx            # Root shell, local fonts, AuthProvider, Nav, CommandPalette, BgNet
│   │   ├── globals.css           # Obsidian · Chrome · Laser CSS tokens & classes
│   │   ├── page.tsx              # Home / Hero / Upload & Column Mapper
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── investigation/page.tsx
│   │   ├── lab/page.tsx
│   │   ├── data/page.tsx
│   │   ├── reports/page.tsx
│   │   ├── profile/page.tsx
│   │   └── not-found.tsx         # Custom Obsidian/Crimson 404 page
│   ├── components/
│   │   ├── AuthProvider.tsx      # Session, CSRF, route guard, per-user dataset (abd_dataset_<uid>)
│   │   ├── Navbar.tsx
│   │   ├── CommandPalette.tsx
│   │   ├── BgNetwork.tsx
│   │   ├── PlotlyChart.tsx       # Client-only dynamic Plotly wrapper (no SSR crash)
│   │   └── ToastProvider.tsx
│   ├── lib/
│   │   ├── api.ts                # CSRF-aware fetch wrapper
│   │   └── format.ts             # INR (₹ en-IN), pctf, safeNext
│   └── types/
│       └── api.ts                # Exact TypeScript interfaces matching FastAPI JSON & OpenAPI schema
├── next.config.mjs
├── package.json
└── tsconfig.json
```

### 5.2 `web/next.config.mjs` (Static Export for Netlify + Local Dev Rewrites)

```javascript
/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5000";
const isStaticExport = process.env.NEXT_OUTPUT_EXPORT === "true";

const nextConfig = {
  // trailingSlash: true ensures static export emits /dashboard/index.html for clean URLs on Netlify
  ...(isStaticExport ? { output: "export", trailingSlash: true } : {}),
  images: { unoptimized: true },
  async rewrites() {
    if (isStaticExport) return [];
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/avatar/:path*", destination: `${backendUrl}/avatar/:path*` },
    ];
  },
};

export default nextConfig;
```

### 5.3 `netlify.toml` (For Next.js on Netlify — replaces root `publish = "frontend"` in Phase 7)
> **Note:** Root `netlify.toml` currently serves the legacy static `frontend/` bundle until `web/` is built in Phase 7.

**Option A — Static Export (`NEXT_OUTPUT_EXPORT=true`, `publish = "web/out"`):**
```toml
[build]
  base = "web"
  command = "NEXT_OUTPUT_EXPORT=true npm run build"
  publish = "out"

[[redirects]]
  from = "/api/*"
  to = "https://your-fastapi-backend.onrender.com/api/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/avatar/*"
  to = "https://your-fastapi-backend.onrender.com/avatar/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/*"
  to = "/404.html"
  status = 404

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"

[[headers]]
  for = "/fonts/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

**Option B — Standard Next.js Runtime (`@netlify/plugin-nextjs`):**
```toml
[build]
  base = "web"
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"

[[redirects]]
  from = "/api/*"
  to = "https://your-fastapi-backend.onrender.com/api/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/avatar/*"
  to = "https://your-fastapi-backend.onrender.com/avatar/:splat"
  status = 200
  force = true
```

### 5.4 `web/src/types/api.ts` (Exact TypeScript Contracts)

```typescript
export type Severity = "low" | "medium" | "high";
export type MetricKind = "sales" | "profit";
export type TargetField =
  | "order_date"
  | "sales"
  | "profit"
  | "product"
  | "category"
  | "region"
  | "quantity"
  | "discount_pct";

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  job_title: string;
  company: string;
  location: string;
  bio: string;
  created_at: string;
  has_avatar: boolean;
  avatar_v: number;
}

export interface Badge {
  id: string;
  icon: string;
  name: string;
  how: string;
  earned: boolean;
}

export interface GamifyStats {
  xp: number;
  level: number;
  title: string;
  xp_into_level: number;
  xp_per_level: number;
  counts: Record<string, number>;
  badges: Badge[];
}

export interface SessionResponse {
  csrf_token: string;
  authenticated: boolean;
  user: UserProfile | null;
  stats: GamifyStats | null;
}

export interface AuthActionResponse {
  ok: boolean;
  next: string;
  csrf_token: string;
  user: UserProfile;
}

export interface QualityIssue {
  type: string;
  count: number;
  detail: string;
  severity: Severity;
}

export interface QualityReport {
  rows_in: number;
  rows_out: number;
  rows_removed: number;
  quality_score: number;
  date_range: [string, string] | [];
  issues: QualityIssue[];
}

export interface DatasetMeta {
  id: string;
  owner: number;
  filename: string;
  upload_date: string;
  row_count: number;
  quality: QualityReport;
}

export interface UploadSuccessResponse {
  dataset: DatasetMeta;
  months: string[];
  source_note: string;
}

export interface UploadNeedsMappingError {
  error: string;
  needs_mapping: true;
  token: string;
  filename: string;
  columns: string[];
  preview: Record<string, string>[];
  suggestions: Record<TargetField, string | null>;
  source_note: string;
}

export interface FilterOptions {
  regions: string[];
  categories: string[];
  products: string[];
  months: string[];
  min_date: string;
  max_date: string;
}

export interface DashboardKPIs {
  total_sales: number;
  total_profit: number;
  profit_margin: number | null;
  total_orders: number;
  units_sold: number;
  avg_order_value: number | null;
}

export interface MonthlyRow {
  month: string;
  sales: number;
  profit: number;
  orders: number;
  days: number;
  margin: number;
  sales_change: number | null;
  profit_change: number | null;
}

export interface GroupRow {
  name: string;
  sales: number;
  profit: number;
  orders: number;
  margin: number;
}

export interface DailyRow {
  date: string;
  sales: number;
  profit: number;
  orders: number;
}

export interface DashboardResponse {
  meta: DatasetMeta;
  options: FilterOptions;
  filtered_rows: number;
  kpis: DashboardKPIs;
  monthly: MonthlyRow[];
  products: GroupRow[];
  categories: GroupRow[];
  regions: GroupRow[];
  daily: DailyRow[];
  heatmap: { regions: string[]; products: string[]; z: number[][] };
  discount_bands: { band: string; sales: number; profit: number; orders: number; margin: number }[] | null;
  forecast: {
    next_month: string;
    history_months: number;
    sales: { projected: number; trend_per_month: number; band: number | null };
    profit: { projected: number; trend_per_month: number; band: number | null };
  } | null;
  pulse: { icon: string; label: string; value: string; detail: string }[];
  health: {
    score: number;
    grade: "Strong" | "Healthy" | "Watch closely" | "At risk";
    parts: { name: string; points: number; max: number; detail: string }[];
  };
}

export interface ContributorRow {
  name: string;
  previous: number;
  current: number;
  delta: number;
  pct: number | null;
  share_of_change: number;
}

export interface DriverChange {
  driver: "orders" | "units" | "avg_selling_price" | "margin" | "avg_discount";
  label: string;
  previous: number;
  current: number;
  change: number;
  unit: "%" | "pts";
}

export interface AnomalyItem {
  date: string;
  sales: number;
  profit: number;
  orders: number;
  typical_daily_sales: number;
  direction: "spike" | "dip";
  score: number;
  methods: string[];
  note: string;
}

export interface InvestigationResponse {
  question: string;
  investigation: {
    metric: MetricKind;
    comparison: {
      metric: MetricKind;
      previous_period: string;
      current_period: string;
      previous: number;
      current: number;
      delta: number;
      pct: number | null;
      direction: "decline" | "increase" | "flat";
      partial_warning: string | null;
    };
    severity: Severity;
    contributors: Record<"category" | "product" | "region" | "segment", ContributorRow[]>;
    drivers: { segment: string; changes: DriverChange[] } | null;
    kpi_changes: Record<"sales" | "profit" | "orders", { previous: number; current: number; pct: number | null }>;
    anomalies: AnomalyItem[];
    monthly_shifts: { month: string; metric: string; change_pct: number }[];
  };
  findings: { finding: string; evidence: string; severity: Severity }[];
  next_checks: string[];
  explanation: { text: string; source: "rules" | "llm"; llm_error?: string };
}

export interface WhatIfSegment {
  name: string;
  orders: number;
  sales: number;
  profit: number;
  prev_orders: number;
}

export interface WhatIfResponse {
  month: string;
  segment: string;
  baseline: { orders: number; sales: number; profit: number; margin: number; month_total_profit: number };
  previous_orders: number;
  restore_order_change_pct: number | null;
  inputs: { order_change_pct: number; price_change_pct: number; margin_change_pts: number };
  scenario: { orders: number; sales: number; profit: number; margin: number };
  delta_sales: number;
  delta_profit: number;
  pct_of_month_profit: number | null;
}

export interface GoalItem {
  metric: MetricKind;
  target: number;
  actual: number;
  pct: number;
  remaining: number;
  days_left: number;
  needed_per_day: number | null;
}

export interface NoteItem {
  id: number;
  text: string;
  created_at: string;
}

export interface PreviewResponse {
  rows: {
    order_date: string;
    product: string;
    category: string;
    region: string;
    quantity: number | null;
    sales: number;
    profit: number | null;
    discount_pct: number | null;
  }[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
```

### 5.5 `web/src/lib/api.ts` (CSRF-Synchronized Client)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

let csrfToken = "";

export function setCsrfToken(token: string) {
  if (token) csrfToken = token;
}

export function getApiUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;
  constructor(message: string, status: number, data: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  onUnauthorized?: () => void;
}

export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    ...(opts.headers || {}),
  };

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    if (opts.body instanceof FormData) {
      body = opts.body;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
  }

  const res = await fetch(getApiUrl(path), {
    method: opts.method || "GET",
    headers,
    body,
    credentials: "include",
  });

  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (typeof data.csrf_token === "string") {
    setCsrfToken(data.csrf_token);
  }

  if (res.status === 401 && data.login_required) {
    opts.onUnauthorized?.();
    throw new ApiError("Please sign in.", 401, data);
  }

  if (!res.ok) {
    throw new ApiError(
      typeof data.error === "string" ? data.error : "Something went wrong",
      res.status,
      data
    );
  }

  return data as T;
}
```

### 5.6 `web/src/components/PlotlyChart.tsx` (SSR-Safe Client Chart)

```tsx
"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => <div className="skel" style={{ height: 320 }} />,
});

export const PALETTE = {
  obsidian: "#050507",
  obsidian2: "#0c0c11",
  silver: "#c9cdd3",
  silverHi: "#f2f4f7",
  silverLo: "#8a9098",
  dim: "#4d525a",
  crimson: "#ff1a40",
  crimsonHi: "#ff4d6d",
  crimsonLo: "#a10020",
};

interface PlotlyChartProps {
  data: Data[];
  layout?: Partial<Layout>;
  style?: React.CSSProperties;
}

export function PlotlyChart({ data, layout = {}, style }: PlotlyChartProps) {
  const mergedLayout: Partial<Layout> = {
    autosize: true,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: PALETTE.silverHi, family: "Inter, system-ui, sans-serif", size: 12 },
    margin: { t: 14, r: 16, b: 40, l: 62 },
    xaxis: { gridcolor: "rgba(201,205,211,.15)", zerolinecolor: "rgba(201,205,211,.15)" },
    yaxis: { gridcolor: "rgba(201,205,211,.15)", zerolinecolor: "rgba(201,205,211,.15)" },
    legend: { orientation: "h", y: 1.16 },
    hoverlabel: { bgcolor: PALETTE.obsidian2, font: { color: PALETTE.silverHi } },
    ...layout,
  };

  return (
    <Plot
      data={data}
      layout={mergedLayout}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: "100%", height: "100%", ...style }}
    />
  );
}
```

### 5.7 `web/src/components/AuthProvider.tsx` (Session & Per-User Dataset Store)

```tsx
"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch, setCsrfToken } from "@/lib/api";
import type { GamifyStats, SessionResponse, UserProfile } from "@/types/api";

interface AuthContextValue {
  loading: boolean;
  sessionError: string | null;
  authenticated: boolean;
  user: UserProfile | null;
  stats: GamifyStats | null;
  datasetId: string | null;
  datasetName: string | null;
  setActiveDataset: (id: string, filename: string) => void;
  refreshSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const PROTECTED = ["/dashboard", "/investigation", "/lab", "/data", "/reports", "/profile"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<GamifyStats | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [datasetName, setDatasetName] = useState<string | null>(null);

  const router = useRouter();
  const pathname = usePathname() || "/";

  const readStoredDataset = useCallback((uid: number) => {
    const key = `abd_dataset_${uid}`;
    setDatasetId(localStorage.getItem(key));
    setDatasetName(localStorage.getItem(`${key}_name`));
  }, []);

  const refreshSession = useCallback(async () => {
    setSessionError(null);
    try {
      const sess = await apiFetch<SessionResponse>("/api/auth/session");
      setCsrfToken(sess.csrf_token);
      if (sess.authenticated && sess.user) {
        setUser(sess.user);
        setStats(sess.stats);
        readStoredDataset(sess.user.id);
      } else {
        setUser(null);
        setStats(null);
        setDatasetId(null);
        setDatasetName(null);
      }
    } catch (err) {
      setSessionError(err instanceof Error ? err.message : "Could not reach backend API.");
    } finally {
      setLoading(false);
    }
  }, [readStoredDataset]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    if (loading || sessionError) return;
    const isProtected = PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`));
    if (!user && isProtected) {
      const search = typeof window !== "undefined" ? window.location.search : "";
      router.replace(`/login?next=${encodeURIComponent(pathname + search)}`);
    } else if (user && (pathname === "/login" || pathname === "/register")) {
      router.replace("/dashboard");
    }
  }, [loading, sessionError, user, pathname, router]);

  const setActiveDataset = useCallback(
    (id: string, filename: string) => {
      if (!user) return;
      const key = `abd_dataset_${user.id}`;
      localStorage.setItem(key, id);
      localStorage.setItem(`${key}_name`, filename);
      setDatasetId(id);
      setDatasetName(filename);
    },
    [user]
  );

  const signOut = useCallback(async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore network/401 on sign out
    }
    if (user) {
      localStorage.removeItem(`abd_dataset_${user.id}`);
      localStorage.removeItem(`abd_dataset_${user.id}_name`);
    }
    setUser(null);
    setStats(null);
    setDatasetId(null);
    setDatasetName(null);
    router.replace("/login");
  }, [user, router]);

  return (
    <AuthContext.Provider
      value={{
        loading,
        sessionError,
        authenticated: Boolean(user),
        user,
        stats,
        datasetId,
        datasetName,
        setActiveDataset,
        refreshSession,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
```

---

## 6. Ordered Implementation Tasks (Synced with `openspec/changes/nextjs-frontend/tasks.md`)

### Phase 1: FastAPI Backend & OpenSpec Contract (Completed)
- [x] Migrate `app.py`, `src/database/db.py`, `src/auth/security.py`, `src/auth/routes.py`, and `src/routes/*.py` from Flask to FastAPI + Uvicorn + Pydantic (`src/schemas.py`).
- [x] Add `GET /api/auth/session`, `GET /api/health`, rotated `csrf_token` + `user` in `/api/auth/login` and `/api/auth/register`, allowlisted `CORS_ORIGINS`, and `X-Forwarded-For` throttling support.
- [x] Update `requirements.txt`, `Procfile`, and `.env.example` for FastAPI/Uvicorn production deployment.
- [x] Export live OpenAPI 3.1 contract to `openspec/openapi.yaml` and verify all 50 pytest cases pass (`python -m pytest -v`).

### Phase 2: Next.js Project Scaffold & Design System
- [ ] Initialize Next.js 15/16 App Router project in `web/` (`npx create-next-app@latest web --ts --app --src-dir --eslint`).
- [ ] Install dependencies: `npm install plotly.js-dist-min react-plotly.js` and `npm install -D @types/plotly.js @netlify/plugin-nextjs`.
- [ ] Copy `static/fonts/*.woff2` into `web/public/fonts/` and wire `next/font/local` for `Inter`, `Space Grotesk`, and `JetBrains Mono` (`--font-inter`, `--font-display`, `--font-mono`).
- [ ] Port `static/css/style.css` into `web/src/app/globals.css`, verifying only Obsidian (`#050507`, `#0c0c11`, `#15151c`), Chrome Silver (`#c9cdd3`, `#f2f4f7`, `#8a9098`, `#4d525a`), and Laser Crimson (`#ff1a40`, `#ff4d6d`, `#a10020`) are used.
- [ ] Create `web/next.config.mjs` with dev rewrites and `NEXT_OUTPUT_EXPORT` toggle (`trailingSlash: true`).

### Phase 3: Core Infrastructure & Auth
- [ ] Add `web/src/types/api.ts`, `web/src/lib/api.ts`, and `web/src/lib/format.ts` (`fmtInr`, `pctf`, `safeNext`).
- [ ] Build `web/src/components/AuthProvider.tsx`, `Navbar.tsx`, `CommandPalette.tsx` (`Ctrl+K`/`Cmd+K`), `BgNetwork.tsx` (respecting `prefers-reduced-motion`), and `ToastProvider.tsx`, plus `web/src/app/not-found.tsx`.
- [ ] Implement `/login` and `/register` pages with password visibility toggle and 5-step password strength meter.

### Phase 4: Home & Data Ingestion
- [ ] Implement `/` (`web/src/app/page.tsx`): Hero section, live KPI/sparkline preview card, demo buttons (`clean` / `dirty`), drag-and-drop file uploader (<=50 MB), and interactive 422 `needs_mapping` column mapper.
- [ ] Verify per-user active dataset persistence under `abd_dataset_<uid>` in `localStorage`.

### Phase 5: Analytics Dashboard & Investigation
- [ ] Create SSR-safe `web/src/components/PlotlyChart.tsx` (`next/dynamic(..., { ssr: false })`).
- [ ] Implement `/dashboard`: Filters (`region`, `category`, `product`, `start`, `end`), Business Pulse cards, Health Score SVG gauge, 6 animated KPI cards, 7 `PlotlyChart` graphs (with `Profit`/`Sales` segment toggles), next-month linear projection, Data Quality report, and `clean.csv` export link.
- [ ] Implement `/investigation`: Natural-language question input (max 300 chars), preset chips, `previous` -> `current` month pickers, `Auto`/`Profit`/`Sales` metric switch, 4-tab contributor bar chart, driver breakdown cards, findings & unusual days cards, next checks, report generation, and `contributors.csv` download.

### Phase 6: The Lab, Data Explorer, Reports & Profile
- [ ] Implement `/lab`: Segment selector, debounced `commit: false` vs release `commit: true` sliders, restore-last-month button, grouped Now vs Scenario bar chart, monthly goals CRUD with circular progress rings, and case notes CRUD (1-500 chars, max 100).
- [ ] Implement `/data`: Searchable, sortable, paginated table (`GET /api/preview`) and cleaned CSV export.
- [ ] Implement `/reports`: Dataset listing, report generation (`POST /api/report/<id>`), and view/download links.
- [ ] Implement `/profile`: Avatar drag-and-drop upload (`<=3 MB`) & deletion, XP/rank/8-badge grid, profile edit form, password change form, and delete-account confirmation modal.

### Phase 7: Verification & Netlify Deployment
- [ ] Run FastAPI tests (`python -m pytest -v`) and verify `/openapi.json` stays green.
- [ ] Run Next.js lint, typecheck, and production build (`cd web && npm run lint && npx tsc --noEmit && NEXT_OUTPUT_EXPORT=true npm run build`).
- [ ] Deploy FastAPI backend (`uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`) to Render/Railway.
- [ ] Update root `netlify.toml` (switching from legacy `publish = "frontend"` to `base = "web"`) with the live backend URL and deploy `web/` to Netlify.
