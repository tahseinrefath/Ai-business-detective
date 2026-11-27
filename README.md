# 🕵️ AI Business Detective

**AI-Powered Business Performance Analysis System** — *Turning Business Data into Actionable Insights.*

Upload a sales file → the app cleans it transparently, builds an interactive dashboard, ranks **which products and regions drove a rise or fall**, flags unusual days with statistics and Isolation Forest, explains the evidence in plain English, and exports printable HTML and CSV reports.

---

## Architecture

AI Business Detective uses a decoupled full-stack architecture designed for **Next.js on Netlify** and **FastAPI on Python cloud hosts**:

| Layer | Stack | Location |
|---|---|---|
| **Frontend (Primary)** | **Next.js 15** (App Router, TypeScript), `plotly.js-dist-min`, self-hosted WOFF2 fonts | [`web/`](web/) |
| **Backend API** | **FastAPI**, **Uvicorn**, Pydantic v2, Starlette `SessionMiddleware`, Pandas, NumPy, scikit-learn | [`app.py`](app.py), [`src/`](src/) |
| **Database & Storage** | SQLite (`data/app.db`) + per-user processed pickle/JSON datasets (`data/processed/`) + optional PostgreSQL mirror (`DATABASE_URL`) | [`src/database/`](src/database/), [`database/`](database/) |
| **Legacy / Fallback UI** | Jinja2 templates (`templates/`) + generated vanilla static bundle (`frontend/` via `scripts/build_frontend.py`) | [`templates/`](templates/), [`frontend/`](frontend/) |
| **OpenSpec & OpenAPI** | Modular OpenSpec specs (`proposal.md`, `design.md`, `tasks.md`, 6 capability specs) + live-exported OpenAPI 3.1 YAML | [`openspec/`](openspec/), [`NEXTJS_FRONTEND_OPENSPEC.md`](NEXTJS_FRONTEND_OPENSPEC.md) |

---

## Design System & Guardrails

* **Obsidian · Chrome · Laser Palette:** Strictly three color families — **Obsidian Black** (`#050507`, `#0c0c11`, `#15151c`), **Chrome Silver** (`#c9cdd3`, `#f2f4f7`, `#8a9098`, `#4d525a`), and **Laser Crimson** (`#ff1a40`, `#ff4d6d`, `#a10020`). Enforced across stylesheets, scripts, templates, and reports by [`tests/test_palette.py`](tests/test_palette.py).
* **Self-Hosted Offline Typography:** `Space Grotesk` (headings), `Inter` (body), and `JetBrains Mono` (tabular numbers & code), bundled in `static/fonts/` and `web/public/fonts/`. Flat monochrome emoji glyphs are preserved with `font-variant-emoji: text` and `\uFE0E`.
* **Evidence-First Analytics Rules:**
  1. Python and Pandas perform every calculation; the explainer only **describes** computed figures.
  2. Contributors show **where** a change happened — never proof of **why** (stated explicitly in the UI and reports).
  3. Missing `profit` values are **never** silently imputed as `0` (documented in [`src/data_processing/cleaner.py`](src/data_processing/cleaner.py)).
  4. A partial latest month triggers a warning instead of a misleading decline.

---

## Core Features

### 1. Multi-Format Ingestion & Interactive Column Mapping
Upload files up to **50 MB** or load one-click demo cases (`clean` or `dirty`):

| Format | Capabilities |
|---|---|
| **Excel** `.xlsx .xlsm .xls` | Scans all sheets, selects the best-matching sheet, and skips title rows above the header |
| **OpenDocument** `.ods` | Smart sheet and header detection |
| **CSV · TSV · TXT** | Auto-detects delimiters for TSV/TXT; handles UTF-8 and Latin-1 |
| **JSON** | List of records, `{"data": [...]}` wrappers, column-oriented dicts, or JSON Lines |
| **PDF** | Extracts text-based tables across multiple pages (*scanned image PDFs cannot be read*) |
| **Power BI** `.pbix` | Best-effort extraction via `pbixray` for embedded/imported models (*DirectQuery/live reports contain no embedded rows*) |

If headers are unrecognized (e.g. `Txn Day`, `Total Bill`, `Shop City`), the backend returns HTTP `422` (`needs_mapping: true`) with a 5-row preview and smart column role suggestions; users confirm `order_date` and `sales` (minimum required) plus optional fields before ingestion completes.

### 2. Interactive Performance Dashboard (`/dashboard`)
* **Filters:** Region, category, product, and start/end date range.
* **Business Pulse:** Automatic factual highlights (top profit product, strongest region, thinnest margin, best month).
* **Business Health Score:** Transparent 0–100 gauge scored across **Growth** (30 pts), **Profitability** (30 pts), **Stability** (20 pts), and **Data quality** (20 pts).
* **7 Interactive Plotly Charts:** Monthly sales/profit/margin combo, daily sales + 7-day rolling mean, product & region horizontal bars with `Profit`/`Sales` toggles, region × product heatmap, category profit share donut, and margin by discount band.
* **Next-Month Projection & Quality Report:** Linear trend extension (requires ≥ 3 months) and full audit of cleaned rows.

### 3. Case Investigation (`/investigation`)
* Ask plain-English questions (e.g. *"Why did profit decrease this month?"*) or pick any two months and metric (`Auto`, `Profit`, `Sales`).
* Ranks contributors across **Product × Region**, **Product**, **Region**, and **Category**.
* Drills into the top segment's drivers (**Order count**, **Units sold**, **Avg selling price**, **Profit margin**, **Avg discount**).
* Flags unusual days via **robust z-score** (median + MAD) and **scikit-learn `IsolationForest`**.
* Generates deterministic rule-based explanations by default, or optional prose rewritten from the same evidence via Anthropic (`ANTHROPIC_API_KEY`).

### 4. What-If Lab, Goals & Notes (`/lab`)
* **What-If Simulator:** Adjust orders (`-80%` to `+100%`), average price (`-30%` to `+30%`), and margin (`-15` to `+15` pts) on any latest-month segment; includes a **Match last month's orders** button. Live drags preview without awarding XP (`commit: false`); releasing commits (`commit: true`).
* **Monthly Goals:** Set `sales` or `profit` targets with circular progress rings and required daily pace.
* **Case Notes:** Private per-dataset notes (1–500 characters, up to 100 notes per dataset).

### 5. Data Explorer (`/data`), Reports (`/reports`) & Profile (`/profile`)
* **Data Explorer:** Debounced search, multi-column sorting, pagination, and cleaned CSV download (`/api/export/<id>/clean.csv`).
* **Automated Reports:** Self-contained dark-themed HTML investigation reports (`/api/report/<id>`) ready for browser **Print → Save as PDF**, plus contributors CSV exports.
* **Accounts & Detective Ranks:** Register/sign in, square-cropped 256×256 PNG avatar upload (≤ 3 MB), profile editor, password rotation, XP levels, 8 earnable badges, account deletion, and a global **`Ctrl+K` / `Cmd+K`** command palette.

---

## Project Structure

```text
Ai-business-detective/
├── app.py                              # FastAPI entrypoint, SessionMiddleware, OpenAPI customizer
├── config.py                           # Environment & path configuration
├── requirements.txt                    # Python dependencies (FastAPI, Uvicorn, Pandas, scikit-learn, etc.)
├── Procfile                            # Production Uvicorn start command
├── netlify.toml                        # Netlify build (web/) & /api/* + /avatar/* proxy rules
├── .env.example                        # Environment variable template
├── src/
│   ├── schemas.py                      # Pydantic v2 request/response models
│   ├── gamify.py                       # XP, detective ranks & 8 badges
│   ├── utils.py                        # INR formatting, pct_change, jsonable conversion
│   ├── auth/                           # Auth routes, CSRF, login throttling, CORS, avatar processing
│   ├── data_processing/                # Multi-format loader, validator, cleaner
│   ├── analytics/                      # KPIs, filters, trends, contribution, anomalies, what-if, health score
│   ├── ai/                             # Rule-based & optional Anthropic LLM explainer
│   ├── database/                       # SQLite schema & per-user dataset repository (+ Postgres mirror)
│   ├── reports/                        # Self-contained HTML report generator
│   └── routes/                         # FastAPI routers (dashboard, upload, data, investigation, features, reports)
├── web/                                # Next.js 15 App Router (TypeScript) frontend
│   ├── public/fonts/                   # Self-hosted WOFF2 fonts
│   ├── src/app/                        # App Router pages (/, /login, /register, /dashboard, /investigation, /lab, /data, /reports, /profile, 404)
│   ├── src/components/                 # AuthProvider, Navbar, CommandPalette, BgNetwork, PlotlyChart, ToastProvider
│   ├── src/lib/                        # CSRF-sync apiFetch client & formatting helpers
│   ├── src/types/                      # TypeScript API contracts
│   ├── next.config.mjs                 # Dev API rewrites & static export toggle
│   └── package.json
├── openspec/                           # Modular OpenSpec plan, capability specs & live openapi.yaml
├── scripts/                            # Sample generator, static frontend builder & local preview proxy
├── data/                               # Sample datasets (data/sample/), SQLite DB & user processed storage
├── database/                           # Optional PostgreSQL schema & queries
├── templates/ & static/                # Jinja2 templates & static assets (used for local FastAPI SSR & tests)
└── tests/                              # 50 automated pytest tests
```

---

## Quick Start (Local Development)

### 1. Run the FastAPI Backend
```bash
# Create & activate virtual environment
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env          # optional: customize SECRET_KEY, CORS_ORIGINS, ANTHROPIC_API_KEY

# Start FastAPI on http://127.0.0.1:5000
python app.py
# Or: uvicorn app:app --reload --port 5000
```
* **Swagger UI:** `http://127.0.0.1:5000/docs`
* **ReDoc:** `http://127.0.0.1:5000/redoc`
* **OpenAPI JSON:** `http://127.0.0.1:5000/openapi.json`

### 2. Run the Next.js Frontend
In a second terminal:
```bash
cd web
npm install
npm run dev                   # Runs on http://localhost:3000
```
`web/next.config.mjs` automatically proxies `/api/*` and `/avatar/*` to `http://127.0.0.1:5000`, keeping cookies and CSRF same-origin during development.

---

## Running Tests & Quality Checks

### Backend Tests (`pytest`)
```bash
python -m pytest -v
```
Runs **50 automated tests** covering auth, CSRF rotation, login lock-out, CORS allowlisting, OpenAPI schema integrity, multi-format loaders, cleaning rules, planted decline detection, Isolation Forest anomaly flagging, what-if math, goals/notes privacy, and strict color-palette enforcement.

### Next.js Frontend Checks
```bash
cd web
npm run typecheck             # tsc --noEmit
npm run lint                  # eslint .
# Static export build for Netlify (Linux/macOS):
NEXT_OUTPUT_EXPORT=true npm run build
# Windows PowerShell:
$env:NEXT_OUTPUT_EXPORT="true"; npm run build
```

---

## Deployment Guide (FastAPI Backend + Netlify Frontend)

### Step 1: Deploy the FastAPI Backend (Render / Railway / Fly.io)
1. Push your repository to GitHub.
2. Create a new **Web Service** on [Render](https://dashboard.render.com/) (or Railway) pointing to your repository:
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` (already defined in [`Procfile`](Procfile)).
3. Configure environment variables:
   * `SECRET_KEY`: strong random hex string (`python -c "import secrets; print(secrets.token_hex(32))"`)
   * `CORS_ORIGINS`: e.g. `https://<your-site>.netlify.app` (comma-separated if multiple)
   * `SESSION_COOKIE_SAMESITE`: `Lax` (when using Netlify proxy redirects) or `None` (if calling the backend domain directly without proxy, with `SESSION_COOKIE_SECURE=True`)
   * `SESSION_COOKIE_SECURE`: `True` in production HTTPS
   * `ANTHROPIC_API_KEY` *(optional)*: enables LLM prose summaries
4. Copy your deployed backend URL (e.g. `https://ai-business-detective-api.onrender.com`).

### Step 2: Deploy the Next.js Frontend to Netlify
1. Update [`netlify.toml`](netlify.toml) with your deployed backend URL:
   ```toml
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
2. Commit and push to GitHub.
3. On [Netlify](https://app.netlify.com/), click **Add new site → Import an existing project**, select your repository, and deploy. Netlify automatically reads [`netlify.toml`](netlify.toml) (`base = "web"`, `command = "NEXT_OUTPUT_EXPORT=true npm run build"`, `publish = "out"`).

---

## API Overview

Full OpenAPI 3.1 schema is exported at [`openspec/openapi.yaml`](openspec/openapi.yaml) and served live at `/openapi.json`.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check (`{"status": "ok"}`) |
| `GET /api/auth/session` | Bootstrap CSRF token, authentication state, user profile & gamify stats |
| `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/logout` | Account lifecycle (returns rotated `csrf_token` + `user` on register/login) |
| `GET/PUT /api/profile` · `POST /api/profile/password` · `POST /api/profile/delete` | Profile management & account deletion |
| `POST/DELETE /api/profile/avatar` · `GET /avatar/me` | Avatar upload (256×256 PNG crop) and retrieval |
| `POST /api/upload` · `POST /api/upload/map` · `POST /api/sample` · `GET /api/datasets` | Ingest, map unrecognized columns, load demo cases, list datasets |
| `GET /api/dashboard` · `GET /api/options` | Filtered KPIs, health score, pulse, charts, forecast & filter options |
| `GET /api/preview` · `GET /api/export/<ds>/clean.csv` · `.../contributors.csv` | Searchable/sortable rows & CSV exports |
| `POST /api/investigate` · `POST /api/ask` | Contribution analysis, drivers, anomalies & plain-English explanation |
| `GET/PUT/DELETE /api/goals` · `GET/POST/DELETE /api/notes` | Monthly targets & private case notes |
| `GET /api/whatif/segments` · `POST /api/whatif` | Single-segment sensitivity simulation |
| `POST /api/report/<ds_id>` · `GET /api/report/<ds_id>` | Generate, view & download self-contained HTML reports |

---

## The Demo Case (Planted, Known Answer)

`data/sample/sample_sales.csv` is synthetic (regenerate with `python scripts/generate_sample_data.py`). October profit drops ~23% compared to September, caused by **Laptop sales in the South** (sharply lower order volume, higher discounts, thinner margin). [`tests/test_contribution.py`](tests/test_contribution.py) asserts the system pinpoints this exact segment and its drivers.
`sample_sales_dirty.csv` demonstrates duplicate removal, invalid-date handling, missing profit preservation, and text standardization.

---

## Accounts & Security Notes

* Passwords are hashed (`scrypt` / `pbkdf2` via Werkzeug) — never stored in plain text.
* `data/app.db`, `data/.secret_key`, `data/avatars/`, `.env`, and `web/.env.local` are git-ignored.
* Every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) requires `X-CSRF-Token` matching the signed `HttpOnly` session cookie; post-login redirects strictly enforce relative same-site paths.
* Every dataset, goal, note, and report is scoped to its owning `user_id` (unauthorized access returns `404`).

---

## Resume Line *(use only what you've run and tested)*

*Built a FastAPI + Pandas analytics API paired with a Next.js (TypeScript) frontend deployed on Netlify that cleans multi-format sales data, ranks product/region contributors to profit changes, flags anomalies with Isolation Forest, and generates evidence-based HTML/CSV reports; validated with 50 automated tests on a dataset with a planted decline.*
