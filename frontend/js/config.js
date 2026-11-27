/**
 * Netlify Frontend Configuration
 *
 * When using Netlify proxy rewrites (configured in netlify.toml and _redirects),
 * API_BASE_URL should remain an empty string ("") so all /api/* calls are
 * proxied seamlessly to your backend without CORS or third-party cookie restrictions.
 *
 * If you are hosting the backend independently and calling it directly without
 * proxying, set window.API_BASE_URL to your backend URL (e.g. "https://api.example.com").
 */
window.API_BASE_URL = window.API_BASE_URL || "";
