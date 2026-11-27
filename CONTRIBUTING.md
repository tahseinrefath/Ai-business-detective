# Contributing to AI Business Detective

Thank you for your interest in contributing! This guide explains the branching strategy, commit conventions, and PR process.

---

## Branching Strategy

```
main   ← production-ready, protected
 └─ prod   ← release candidate (CI full test suite)
     └─ uat    ← user-acceptance testing
         └─ dev    ← integration branch
             └─ feature/<name>   ← your work branch
```

Always branch from **`dev`** and open PRs back to **`dev`**.

---

## Getting Started

```bash
git clone https://github.com/tahseinrefath/Ai-business-detective.git
cd Ai-business-detective

# Python backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Node frontend
cd web
npm install
cp .env.example .env.local    # fill in BACKEND_URL
npm run dev
```

---

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Build / tooling / config |
| `test` | Adding or fixing tests |
| `refactor` | Code change without feature or fix |
| `perf` | Performance improvement |

### Examples

```
feat(web): add CSV export button to data explorer
fix(api): handle empty dataset gracefully in /api/analyse
docs: update README quickstart for Netlify deploy
chore(deps): upgrade fastapi to 0.115.x
```

---

## Pull Request Process

1. Open a draft PR early so the team can follow progress
2. Fill in the PR template (description, type of change, test checklist)
3. All 50 pytest tests must pass + `npm run typecheck` must be clean
4. Assign at least one reviewer
5. Squash-merge into `dev`

---

## Code Style

- **Python:** `black` + `ruff` (line length 88)
- **TypeScript/TSX:** ESLint + Prettier (configured in `web/eslint.config.mjs`)
- **CSS:** BEM-ish classes; use only the Obsidian/Chrome/Laser palette variables

---

## Running Tests

```bash
# Backend
python -m pytest -v

# Frontend type-check
cd web && npm run typecheck

# Frontend lint
cd web && npm run lint

# Palette audit (must stay zero violations)
python tests/test_palette.py
```

---

## Reporting Issues

Use GitHub Issues with one of the labels:
- `bug` – something is broken
- `enhancement` – feature request
- `documentation` – docs gap
- `question` – general question
