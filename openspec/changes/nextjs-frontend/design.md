# Technical Design: Next.js Frontend + FastAPI Backend (`nextjs-frontend`)

## 1. System Topology & Netlify Deployment

```text
Browser (https://<site>.netlify.app)
   │
   ├── GET /, /dashboard, /investigation, /lab, /data, /reports, /profile, /login, /register
   │       └── Served by Netlify (Next.js static export `web/out` OR `@netlify/plugin-nextjs`)
   │
   └── /api/* & /avatar/* (Same-Origin Requests with HttpOnly Cookie + X-CSRF-Token)
           │
           ├── Local Dev:  next.config.mjs rewrites -> http://127.0.0.1:5000
           └── Production: netlify.toml [[redirects]] (status = 200, force = true)
                             -> https://<fastapi-backend>.onrender.com/{api,avatar}/:splat
```

### Why Reverse Proxy on Netlify Is Preferred
1. Browsers treat `/api/*` and `/avatar/*` as **same-origin** (`<site>.netlify.app`), eliminating third-party cookie blocking in Safari/Chrome/Firefox.
2. FastAPI's `SessionMiddleware` keeps `same_site="lax"` safely without requiring cross-site cookie exemptions.
3. If `NEXT_PUBLIC_API_BASE_URL` is ever set directly (bypassing proxy), FastAPI supports allowlisted `CORS_ORIGINS` (`Vary: Origin`, `Access-Control-Allow-Credentials: true`) when `SESSION_COOKIE_SAMESITE=None` and `SESSION_COOKIE_SECURE=True`.

---

## 2. CSRF Synchronization Across FastAPI & Next.js SPA

In FastAPI (`src/auth/security.py`), `log_in(request, user_id)` clears the pre-login session and generates a fresh `request.session["csrf"]`. In a Next.js SPA (client-side `router.push()`), there is no full-page Jinja render to refresh `<meta name="csrf-token">`.

**Design Solution:**
1. `AuthProvider` calls `GET /api/auth/session` on initial mount (`credentials: "include"`). FastAPI initializes `session["csrf"]` and returns `{ csrf_token, authenticated, user, stats }`.
2. `apiFetch()` in `web/src/lib/api.ts` intercepts **every** JSON response: whenever `data.csrf_token` is present (including `POST /api/auth/login` and `POST /api/auth/register`), it updates the module-level `csrfToken` immediately before subsequent requests run.
3. Every `POST`, `PUT`, `PATCH`, and `DELETE` attaches `X-CSRF-Token: <csrfToken>`.

---

## 3. Plotly SSR-Safe Integration

`plotly.js` accesses `window` and `self` on import, which breaks Next.js server rendering (`next build`).
- Dynamically import `plotly.js-dist-min` inside `useEffect` in `"use client"` component `web/src/components/PlotlyChart.tsx`, rendering with `Plotly.react` and resizing via `ResizeObserver` (avoids React 19 peer dependency conflicts with `react-plotly.js`).
- Centralize Obsidian/Chrome/Laser chart defaults (`paper_bgcolor: "rgba(0,0,0,0)"`, `plot_bgcolor: "rgba(0,0,0,0)"`, `Inter` font, `--line` grid color, `#0c0c11` hoverlabel).

- **Typography Binding (`layout.tsx` + `globals.css`)**: Load the self-hosted `.woff2` files via `next/font/local` exposing CSS variables `--font-inter`, `--font-display`, and `--font-mono`, and bind `--font: var(--font-inter), system-ui, "Segoe UI", sans-serif; --display: var(--font-display), var(--font-inter), system-ui, sans-serif; --mono: var(--font-mono), ui-monospace, Consolas, monospace;` in `globals.css`.

---

## 4. Corrected Next.js Starter Code

### 4.1 `web/next.config.mjs`
```javascript
/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5000";
const isStaticExport = process.env.NEXT_OUTPUT_EXPORT === "true";

const nextConfig = {
  // trailingSlash: true ensures static export produces /dashboard/index.html for clean URLs on Netlify
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

### 4.2 `netlify.toml` (for `web/` on Netlify — replaces root `publish = "frontend"` in Phase 7)
> **Note:** The repository root `netlify.toml` currently targets the legacy static `frontend/` directory (`publish = "frontend"`) until `web/` is scaffolded in Phase 7.

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

### 4.3 `web/src/lib/api.ts`
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

export async function apiFetch<T>(
  path: string,
  opts: {
    method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    body?: unknown;
    headers?: Record<string, string>;
    onUnauthorized?: () => void;
  } = {}
): Promise<T> {
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
  if (typeof data.csrf_token === "string") setCsrfToken(data.csrf_token);

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

### 4.4 `web/src/lib/format.ts`
```typescript
export function fmtInr(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "n/a";
  const sign = n < 0 ? "-" : "";
  return `${sign}₹${Math.abs(Math.round(n)).toLocaleString("en-IN")}`;
}

export function pctf(n: number | null | undefined, digits = 1): string {
  if (n == null || Number.isNaN(n)) return "n/a";
  return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

export function safeNext(url: string | null | undefined): string {
  if (url && url.startsWith("/") && !url.startsWith("//") && !url.includes("\\")) {
    return url;
  }
  return "/dashboard";
}
```

### 4.5 `web/src/components/PlotlyChart.tsx`
```tsx
"use client";

import { useEffect, useRef } from "react";
import type { Config, Data, Layout } from "plotly.js";

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
  good: "#f2f4f7",
  bad: "#ff1a40",
};

export function PlotlyChart({
  data,
  layout = {},
  className,
  style,
}: {
  data: Data[];
  layout?: Partial<Layout>;
  className?: string;
  style?: React.CSSProperties;
}) {
  const elRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    let observer: ResizeObserver | null = null;
    if (!elRef.current) return;

    (async () => {
      const mod = await import("plotly.js-dist-min");
      if (!active || !elRef.current) return;
      const Plotly = mod.default || mod;
      const merged: Partial<Layout> = {
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
      const config: Partial<Config> = { displayModeBar: false, responsive: true };
      await Plotly.react(elRef.current, data, merged, config);
      if (typeof ResizeObserver !== "undefined" && elRef.current) {
        observer = new ResizeObserver(() => {
          if (elRef.current) Plotly.Plots.resize(elRef.current);
        });
        observer.observe(elRef.current);
      }
    })();

    return () => {
      active = false;
      observer?.disconnect();
    };
  }, [data, layout]);

  return <div ref={elRef} className={className} style={{ width: "100%", minHeight: 280, ...style }} />;
}
```

### 4.6 `web/src/components/AuthProvider.tsx`
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
      // Ignore logout errors if session already expired
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
