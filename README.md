# 🕵️ AI Business Detective
**AI-Powered Business Performance Analysis System** — *Turning Business Data into Actionable Insights.*

Upload a sales file → the app cleans it, builds a dashboard, finds **which products/regions drove a rise or fall**,
flags unusual days, explains the evidence in plain English and exports a report.

## What's new in v6 — Obsidian · Chrome · Laser
**Design:** strictly three colours — *obsidian black* surfaces, *chrome silver* text/metal/data, *laser crimson* for action and alerts.
Self-hosted fonts (works offline): **Space Grotesk** (headings), **Inter** (text), **JetBrains Mono** (numbers). Emoji are rendered as flat monochrome glyphs.
A test (`tests/test_palette.py`) scans every CSS/JS/template/report file and fails if any colour leaves the palette.

**Accounts:** register / sign in / sign out, password hashing, CSRF protection, login lock-out after 5 wrong tries, per-user datasets
(other users get a 404), profile editing, **profile-picture upload** (verified, cropped square, re-encoded to PNG), password change, delete-account.

**New features:** 🧪 *Lab* (what-if simulator, monthly goals with daily pace, case notes) · ❤ *business health score* (transparent formula) ·
🏅 detective ranks & badges · ⌨ command palette (**Ctrl K**).

## What's new in v4 — "Help me read your columns"
If your file's headers aren't recognised (e.g. `Txn Day`, `Total Bill`, `Shop City`), the app no longer just fails: it shows your real columns and a
preview, pre-selects its best guess for each role, and lets you confirm. Only **Date** and **Sales** are required; a missing profit column is allowed
(profit then shows as 0 and the data-quality report says so). 48 automated tests.

## What's new in v3 — upload almost any file
| Format | Notes |
|---|---|
| Excel `.xlsx .xlsm .xls` | all sheets scanned; the one matching your columns is used; title rows above the header are skipped |
| OpenDocument `.ods` | same smart sheet/header detection |
| CSV · TSV · TXT | delimiter auto-detected for TSV/TXT; UTF-8 or Latin-1 |
| JSON | list of records, `{"data": [...]}` wrappers, or JSON Lines |
| PDF | tables with a real text layer, including tables that continue over several pages. **Scanned PDFs (images) cannot be read** |
| Power BI `.pbix` | best effort via `pbixray`. Works when data is *imported* into the file. Live-connection / DirectQuery reports contain no data - export a table to CSV/Excel instead. Not tested against real .pbix files in the test-suite |

Column names are matched flexibly (`Date`, `Revenue`, `Qty`, `City`… are recognised). Upload limit: 50 MB. 48 automated tests.

## What's new in v2
* 🎨 Redesigned UI: aurora background, glass cards, animated KPIs, scroll reveals, **light/dark theme toggle**
* 🎛️ Dashboard **filters** (region, category, product, date range) + **business pulse** highlights
* 🗺️ New charts: region × product **heatmap**, category donut, **margin by discount level**, next-month **trend projection**
* 🔍 Investigation: **pick any two months**, choose profit / sales, export **contributors CSV**
* 🗂️ New **Data explorer** page (search, sort, paginate) and **cleaned-data CSV export**
* 📄 Report now includes a monthly chart · 15 automated tests

## Features
| | |
|---|---|
| 🧹 Data cleaning | duplicates, invalid dates, missing values, messy text, currency symbols — every fix is reported |
| 📊 Dashboard | KPIs, filters, monthly + daily trends, product / region / category views, heatmap, discount analysis, trend projection |
| 🔍 Investigation | month-over-month change → contributors by product / region / category / product×region → drivers (orders, price, margin, discount) |
| 🚨 Anomalies | robust z-score + scikit-learn `IsolationForest` |
| 💬 Ask a question | "Why did profit decrease this month?" — rule-based explainer by default, optional LLM |
| 📄 Reports | self-contained HTML (Print → Save as PDF) |

## Run it
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                                           # http://127.0.0.1:5000
```
Click **Try the demo case** on the home page. Run tests with `pytest`.

## The demo case (planted, known answer)
`data/sample/sample_sales.csv` is synthetic (regenerate: `python scripts/generate_sample_data.py`).
October profit falls ~23 % vs September. The planted cause: **Laptop sales in the South** — far fewer orders,
heavier discounts, thinner margin. The tests assert the system finds it (`tests/test_contribution.py`).
`sample_sales_dirty.csv` has duplicates, bad dates, missing profit and messy text to showcase cleaning.
`sample_sales_mini.csv` is the original 7-row file from your chat export.

## Design rules (from the project brief)
* Python/pandas calculate; the explainer only **describes** calculated numbers.
* A contributor shows **where** a change happened — not proof of **why**. The text says so.
* Missing profit is **never** silently set to 0 (documented in `cleaner.py`).
* A partial latest month triggers a warning instead of a fake "decline".
* Never commit `.env`, API keys or private business data.

## Optional integrations
* **LLM explanations:** set `ANTHROPIC_API_KEY` in `.env` (copy `.env.example`). Same evidence, smoother prose; falls back to rules on any error.
* **PostgreSQL:** run `database/schema.sql`, set `DATABASE_URL`. Dataset metadata is mirrored; analysis runs on cleaned data stored in `data/processed/`.
  *(Mirroring `sales` rows, `analysis_runs`, `insights` and `reports` tables is the natural next step — SQL for them is already in `schema.sql`.)*

## API
| Endpoint | Purpose |
|---|---|
| `POST /api/upload` · `POST /api/sample` | ingest + clean a dataset |
| `GET /api/dashboard?dataset=ID&region=&category=&product=&start=&end=` | filtered KPIs and chart data |
| `GET /api/options` · `GET /api/preview` | filter options · searchable data rows |
| `GET /api/export/<id>/clean.csv` · `.../contributors.csv` | CSV downloads |
| `POST /api/investigate` · `POST /api/ask` | run an investigation / ask a question |
| `POST /api/report/<id>` · `GET /api/report/<id>` | create / fetch the HTML report |

## Structure
`app.py` · `config.py` · `src/data_processing` (loader, validator, cleaner) · `src/analytics` (kpi, trends, contribution, anomaly_detection, investigation) ·
`src/ai` (prompts, insight_generator) · `src/database` · `src/reports` · `src/routes` · `templates/` · `static/` · `tests/` · `database/`

## Resume line (use only what you've run and tested)
*Built a Flask + Pandas analytics app that cleans sales data, ranks product/region contributors to profit changes, flags anomalies with Isolation Forest and generates evidence-based reports; validated on a dataset with a planted, known decline.*


## Accounts & security notes
* Passwords are hashed (scrypt/pbkdf2) - never stored in plain text. `data/app.db` (accounts), `data/.secret_key` and `data/avatars/` are git-ignored.
* Every state-changing request needs the CSRF token; only same-site relative redirects are allowed after sign-in.
* This is built for **local / learning use**. Before exposing it on the internet, serve it behind HTTPS with a production server (e.g. gunicorn) and
  set `SESSION_COOKIE_SECURE=True`. Email verification and password reset are not included.
