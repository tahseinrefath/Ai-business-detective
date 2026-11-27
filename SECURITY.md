# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅ Yes |
| 0.2.x   | ⚠️ Security fixes only |
| < 0.2   | ❌ No |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Email: `security@example.com` (replace with real address before production)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We will acknowledge within **48 hours** and aim to release a patch within **7 days** for critical issues.

## Security Design

- **CSRF protection:** Double-submit cookie pattern with rotating tokens on every auth state change
- **Brute-force protection:** `LoginThrottle` — 5 failed attempts locks account for 10 minutes
- **Session cookies:** `HttpOnly`, `SameSite=Lax`, `Secure` in production
- **CORS:** Strict allowlist via `ALLOWED_ORIGINS` env variable
- **Input validation:** All inputs validated by Pydantic v2 models before reaching business logic
- **SQL injection:** All queries use parameterised statements (never string interpolation)
- **File uploads:** MIME-type checked server-side; only `text/csv` accepted for datasets
- **Secrets:** Never committed — loaded from environment variables via `python-dotenv`
