# Project Context: AI Business Detective

## Overview
**AI Business Detective** is an evidence-first business performance analytics platform. Users upload sales files (`.csv`, `.tsv`, `.txt`, `.xlsx`, `.xlsm`, `.xls`, `.ods`, `.json`, `.pdf`, `.pbix`) or load planted demo cases; the backend cleans the data transparently, computes KPIs, identifies which products/regions drove a rise or fall, flags unusual days via robust z-score + scikit-learn `IsolationForest`, explains the evidence in plain English, and generates printable HTML reports.

## Architecture & Tech Stack
- **Backend API**: Python 3.12+, **FastAPI** (`app.py`, `src/schemas.py`), **Uvicorn** (`Procfile`), **Starlette `SessionMiddleware`**, **Pandas**, **NumPy**, **scikit-learn**, **Pillow**, **openpyxl**, **xlrd**, **odfpy**, **pdfplumber**, **pbixray**, optional **Anthropic SDK** (`ANTHROPIC_API_KEY`), and **SQLite** (`data/app.db`, optional PostgreSQL metadata mirror via `DATABASE_URL`).
- **Frontend (Target Migration)**: **Next.js (App Router + TypeScript)** deployed on **Netlify**, communicating with the FastAPI backend via Netlify proxy rewrites (`/api/*`, `/avatar/*`) or allowlisted CORS (`CORS_ORIGINS`).
- **Legacy / Current Views**: Jinja2 templates (`templates/*.html`) + static vanilla JS (`static/js/*.js`) and generated static Netlify bundle (`frontend/` via `scripts/build_frontend.py`).
- **OpenAPI Spec**: Live-exported from FastAPI `app.openapi()` at [openspec/openapi.yaml](../openspec/openapi.yaml) (and served at `/openapi.json`, `/docs`, `/redoc`).

## Non-Negotiable Design & Engineering Rules
1. **Strict 3-Family Color Palette** (enforced by `tests/test_palette.py`):
   - **Obsidian Black** (`max(R,G,B) <= 64`): `#050507`, `#0c0c11`, `#15151c`
   - **Chrome Silver** (`max - min <= 16`): `#c9cdd3`, `#f2f4f7`, `#8a9098`, `#4d525a`
   - **Laser Crimson** (`R >= 140, G <= 100, B <= 120, R - G >= 90`): `#ff1a40`, `#ff4d6d`, `#a10020`
   - **Forbidden**: Any colors outside those three families; any theme/accent switcher (`data-accent`, `setAccent`).
2. **Self-Hosted Offline Fonts** (`static/fonts/*.woff2`):
   - `Space Grotesk` (display headings), `Inter` (body text), `JetBrains Mono` (tabular numbers & code).
3. **Flat Monochrome Emojis**:
   - CSS `font-variant-emoji: text` on `body` plus `\uFE0E` variation selector handling.
4. **Evidence-First Analytics Guardrails**:
   - Python/Pandas performs every calculation; the AI/rule explainer ONLY describes calculated numbers.
   - UI must explicitly state that contributors show *where* a change happened, not proof of *why*.
   - Missing `profit` values are never silently imputed as `0` (`cleaner.py`).
   - Partial latest months trigger a `partial_warning` instead of a fake decline (`trends.py`).
5. **Security & Privacy**:
   - Per-user dataset ownership enforcement (`owner == user.id`, returning `404` for unauthorized IDs).
   - Signed `HttpOnly` session cookies + `X-CSRF-Token` validation on `POST`, `PUT`, `PATCH`, `DELETE`.
   - Login throttling: 5 wrong attempts per IP+email lock for 300s (`429`).
   - XSS protection: user-supplied strings (`notes`, `filename`, profile fields) rendered via safe escaping / React JSX interpolation (never `dangerouslySetInnerHTML`).

## Verification Commands
- Backend & Palette Tests: `python -m pytest -v`
- Export Live OpenAPI Schema: `python -c "import pathlib, yaml; from app import app; pathlib.Path('openspec/openapi.yaml').write_text(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True), encoding='utf-8')"`
- Local FastAPI Server: `python app.py` (or `uvicorn app:app --reload --port 5000`)
