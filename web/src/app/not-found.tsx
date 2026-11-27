import Link from "next/link";

export default function NotFound() {
  return (
    <div className="card glow" style={{ textAlign: "center", padding: "60px 24px", marginTop: 40 }}>
      <div style={{ fontSize: 56 }}>🕵️</div>
      <h1 style={{ fontSize: 32, margin: "12px 0 6px" }}>
        Case not found <span className="hot">(404)</span>
      </h1>
      <p className="muted" style={{ fontSize: 16, maxWidth: 500, margin: "0 auto 24px" }}>
        The clue or page you are looking for does not exist, was moved, or has expired.
      </p>
      <div className="row" style={{ justifyContent: "center", gap: 12 }}>
        <Link className="btn" href="/">
          Return to Home
        </Link>
        <Link className="btn ghost" href="/dashboard">
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
