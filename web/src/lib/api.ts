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
    if (typeof window !== "undefined") {
      const cur = window.location.pathname + window.location.search;
      window.location.href = `/login?next=${encodeURIComponent(cur)}`;
    }
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
