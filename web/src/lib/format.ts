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

export function initialsOf(name: string | null | undefined): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  return (parts.slice(0, 2).map((p) => p[0]).join("") || "?").toUpperCase();
}
