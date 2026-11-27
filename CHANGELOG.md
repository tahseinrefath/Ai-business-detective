# Changelog

All notable changes to **AI Business Detective** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
- What-if scenario engine with commit toggle
- Goals CRUD with radial progress rings
- Investigation Q&A with Gemini 1.5 Flash

---

## [0.3.0] – 2026-11-25

### Added
- Next.js 15 App Router frontend (`web/`)
- Static export via `NEXT_OUTPUT_EXPORT=true`
- Netlify deployment config (`netlify.toml`)
- Plotly.js charts: revenue trend, category breakdown, anomaly scatter, funnel, heatmap, forecast
- Command palette (Ctrl+K) with fuzzy search
- Animated particle background (`BgNetwork`)
- Toast notification system
- Password strength meter (5-step)
- Dataset explorer with sort/search/paginate

### Changed
- API base changed from `/` to `/api/` prefix throughout

### Fixed
- CSRF token rotation on login/register
- `Client.delete()` json body workaround in test client

---

## [0.2.0] – 2026-11-20

### Added
- FastAPI migration (from Flask)
- Pydantic v2 request/response schemas
- `ContextVar`-scoped SQLite connection
- `LoginThrottle` brute-force protection (5 attempts / 10 min)
- Custom OpenAPI schema post-processor (`custom_openapi()`)
- `text/csv`, `text/html`, `image/png` media types declared

### Changed
- `Procfile` updated to Uvicorn
- `requirements.txt` now includes `fastapi`, `uvicorn[standard]`, `python-multipart`

### Removed
- All Flask dependencies (`flask`, `flask-cors`, `flask-login`)

---

## [0.1.0] – 2026-11-10

### Added
- Initial project scaffold
- SQLite database with users, datasets, goals, notes tables
- Gemini AI integration for natural-language business analysis
- Revenue trend, category, and anomaly detection analytics
- 50 pytest tests (all passing)
- Obsidian / Chrome / Laser colour palette enforced by `tests/test_palette.py`
