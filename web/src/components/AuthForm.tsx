"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { apiFetch, setCsrfToken } from "@/lib/api";
import { safeNext } from "@/lib/format";
import type { AuthActionResponse } from "@/types/api";

const STRENGTH_LABELS = ["Too weak", "Weak", "Okay", "Good", "Strong"];
const STRENGTH_COLORS = ["#ff1a40", "#ff1a40", "#8a9098", "#c9cdd3", "#f2f4f7"];

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { refreshSession } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = safeNext(searchParams.get("next"));

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const strength = useMemo(() => {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Za-z]/.test(password) && /\d/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password) || (/[a-z]/.test(password) && /[A-Z]/.test(password))) score++;
    return score;
  }, [password]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErr("");
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setErr("Please fill in your email and password.");
      return;
    }
    const body: Record<string, string> = { email: trimmedEmail, password, next: nextUrl };
    if (mode === "register") {
      const trimmedName = name.trim();
      if (trimmedName.length < 2) {
        setErr("Please enter your name (at least 2 characters).");
        return;
      }
      if (password !== password2) {
        setErr("The two passwords do not match.");
        return;
      }
      body.name = trimmedName;
    }

    setSubmitting(true);
    try {
      const r = await apiFetch<AuthActionResponse>(`/api/auth/${mode}`, {
        method: "POST",
        body,
      });
      if (r.csrf_token) setCsrfToken(r.csrf_token);
      await refreshSession();
      router.replace(safeNext(r.next || nextUrl));
    } catch (error) {
      setErr(error instanceof Error ? error.message : "Something went wrong");
      setSubmitting(false);
    }
  };

  return (
    <section className="auth">
      <aside className="auth-art">
        <span className="eyebrow">
          <i /> Your private case room
        </span>
        <h2>
          Solve the case
          <br />
          behind your <span className="grad">numbers</span>.
        </h2>
        <ul>
          <li>
            <i>🔐</i>
            <div>
              <b>Your data stays yours</b>Every dataset is tied to your account. Nobody else can open it.
            </div>
          </li>
          <li>
            <i>🧪</i>
            <div>
              <b>Test ideas before you try them</b>What-if lab, monthly goals and case notes — all saved to your profile.
            </div>
          </li>
          <li>
            <i>🏅</i>
            <div>
              <b>Earn your detective rank</b>Collect badges as you upload, investigate and report.
            </div>
          </li>
        </ul>
        <svg className="float" viewBox="0 0 300 220" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="ag" x1="0" x2="1">
              <stop offset="0" stopColor="var(--a1)" />
              <stop offset="1" stopColor="var(--a3)" />
            </linearGradient>
          </defs>
          <rect x="20" y="130" width="34" height="70" rx="8" fill="var(--a1)" opacity=".7" />
          <rect x="70" y="95" width="34" height="105" rx="8" fill="var(--a2)" opacity=".8" />
          <rect x="120" y="60" width="34" height="140" rx="8" fill="var(--a3)" opacity=".85" />
          <path d="M10 120 C70 90 110 60 170 70 S250 30 290 20" stroke="url(#ag)" strokeWidth="5" strokeLinecap="round" />
        </svg>
      </aside>

      <div className="auth-form">
        <div className="auth-box fade">
          {mode === "login" ? (
            <>
              <h1>Welcome back</h1>
              <p className="sub">Sign in to continue your investigation.</p>
            </>
          ) : (
            <>
              <h1>Create your account</h1>
              <p className="sub">Free, secure and takes under a minute.</p>
            </>
          )}

          {err && (
            <div className="err" role="alert">
              {err}
            </div>
          )}

          <form onSubmit={(e) => void onSubmit(e)} noValidate autoComplete="on">
            {mode === "register" && (
              <div className="field">
                <label htmlFor="name">Full name</label>
                <input
                  id="name"
                  name="name"
                  autoComplete="name"
                  maxLength={60}
                  placeholder="e.g. Asha Kumar"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={120}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type={showPw ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                maxLength={128}
                placeholder={
                  mode === "login"
                    ? "Your password"
                    : "At least 8 characters, with a letter and a number"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="eye"
                aria-label={showPw ? "Hide password" : "Show password"}
                onClick={() => setShowPw((v) => !v)}
              >
                {showPw ? "🙈" : "👁"}
              </button>
              {mode === "register" && (
                <>
                  <div className="meter">
                    <i
                      style={{
                        width: `${password ? (strength + 1) * 20 : 0}%`,
                        background: STRENGTH_COLORS[strength],
                      }}
                    />
                  </div>
                  <div className="hint2">
                    {password
                      ? STRENGTH_LABELS[strength] +
                        (strength < 3 ? " — add length, a number or a symbol" : "")
                      : "Use 8+ characters with letters and numbers."}
                  </div>
                </>
              )}
            </div>

            {mode === "register" && (
              <div className="field">
                <label htmlFor="password2">Confirm password</label>
                <input
                  id="password2"
                  type={showPw ? "text" : "password"}
                  autoComplete="new-password"
                  maxLength={128}
                  placeholder="Repeat your password"
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  required
                />
              </div>
            )}

            <button
              className="btn"
              style={{ width: "100%", justifyContent: "center", padding: 15 }}
              type="submit"
              disabled={submitting}
            >
              {submitting
                ? mode === "login"
                  ? "Signing in…"
                  : "Creating account…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <p className="swap">
            {mode === "login" ? (
              <>
                New here? <Link href="/register">Create an account</Link>
              </>
            ) : (
              <>
                Already have an account? <Link href="/login">Sign in</Link>
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  );
}
