"""Extra analysis: forecast, discount bands, heatmap, business pulse."""
import numpy as np
import pandas as pd


def forecast_next_month(monthly: list[dict]):
    """Straight-line projection of the next month from the monthly history (>=3 months).

    This is a simple trend extension, NOT a reliable prediction - the UI labels it that way.
    """
    if len(monthly) < 3:
        return None
    x = np.arange(len(monthly))
    out = {"next_month": str(pd.Period(monthly[-1]["month"]) + 1), "history_months": len(monthly)}
    for m in ("sales", "profit"):
        y = np.array([r[m] for r in monthly], dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        resid = y - (slope * x + intercept)
        out[m] = {"projected": float(slope * len(x) + intercept), "trend_per_month": float(slope),
                  "band": float(1.5 * resid.std()) if len(y) > 2 else None}
    return out


def discount_bands(df: pd.DataFrame):
    if "discount_pct" not in df or df["discount_pct"].notna().sum() < 20:
        return None
    d = df[df["discount_pct"].notna() & df["profit"].notna()].copy()
    d["band"] = pd.cut(d["discount_pct"], [-0.01, 2, 5, 10, 100], labels=["0-2%", "2-5%", "5-10%", "10%+"])
    g = d.groupby("band", observed=True).agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("sales", "size"))
    g["margin"] = g["profit"] / g["sales"] * 100
    return g.reset_index().astype({"band": str}).to_dict("records")


def heatmap(df: pd.DataFrame, metric="profit"):
    p = df.pivot_table(index="region", columns="product", values=metric, aggfunc="sum").fillna(0)
    return {"regions": p.index.tolist(), "products": p.columns.tolist(), "z": p.values.round(0).tolist()}


def business_pulse(df: pd.DataFrame, monthly: list[dict]) -> list[dict]:
    """Short, factual highlights for the top of the dashboard."""
    if df.empty:
        return []
    pulse = []
    by_p = df.groupby("product").agg(profit=("profit", "sum"), sales=("sales", "sum"))
    by_p["margin"] = by_p["profit"] / by_p["sales"] * 100
    by_r = df.groupby("region")["profit"].sum()
    best_p, best_r = by_p["profit"].idxmax(), by_r.idxmax()
    pulse.append({"icon": "🏆", "label": "Top profit product", "value": best_p, "detail": f"₹{by_p.loc[best_p,'profit']:,.0f} profit"})
    pulse.append({"icon": "🌍", "label": "Strongest region", "value": best_r, "detail": f"₹{by_r.max():,.0f} profit"})
    low = by_p["margin"].idxmin()
    pulse.append({"icon": "⚠️", "label": "Thinnest margin", "value": low, "detail": f"{by_p.loc[low,'margin']:.1f}% margin"})
    if monthly:
        bm = max(monthly, key=lambda r: r["profit"])
        pulse.append({"icon": "📅", "label": "Best month", "value": bm["month"], "detail": f"₹{bm['profit']:,.0f} profit"})
    return pulse


def health_score(df: pd.DataFrame, monthly: list[dict], quality_score: float | None = None) -> dict:
    """A transparent 0-100 'business health' score. NOT an industry standard - the formula is shown to the user.

    growth        30 pts  latest vs previous month sales: -20% -> 0 pts, +10% or more -> 30 pts (neutral 15 if unknown / partial month)
    profitability 30 pts  profit margin: 0% -> 0 pts, 20% or more -> 30 pts
    stability     20 pts  steadiness of daily sales (coefficient of variation): 1.0+ -> 0 pts, 0.3 or less -> 20 pts
    data quality  20 pts  the data-quality score from cleaning (0-100) scaled to 20
    """
    from .trends import partial_month_warning

    clamp = lambda v, lo=0.0, hi=1.0: max(lo, min(hi, v))
    parts = []

    # growth
    growth_pts, growth_note = 15.0, "Needs two months of data - neutral score."
    if len(monthly) >= 2:
        prev, cur = monthly[-2], monthly[-1]
        if partial_month_warning(df, prev["month"], cur["month"]):
            growth_note = f"{cur['month']} is incomplete, so growth is scored neutral."
        elif prev["sales"]:
            g = (cur["sales"] - prev["sales"]) / abs(prev["sales"]) * 100
            growth_pts, growth_note = clamp((g + 20) / 30) * 30, f"Sales {g:+.1f}% vs previous month."
    parts.append({"name": "Growth", "points": growth_pts, "max": 30, "detail": growth_note})

    # profitability
    has_p = df["profit"].notna()
    base = float(df.loc[has_p, "sales"].sum())
    margin = float(df.loc[has_p, "profit"].sum()) / base * 100 if base else None
    parts.append({"name": "Profitability", "points": clamp((margin or 0) / 20) * 30 if margin is not None else 0.0, "max": 30,
                  "detail": f"Profit margin {margin:.1f}%." if margin is not None else "No profit data."})

    # stability
    daily = df.groupby(df["order_date"].dt.normalize())["sales"].sum()
    if len(daily) >= 7 and daily.mean() > 0:
        cv = float(daily.std() / daily.mean())
        parts.append({"name": "Stability", "points": clamp((1.0 - cv) / 0.7) * 20, "max": 20, "detail": f"Daily sales vary by {cv * 100:.0f}% around the average."})
    else:
        parts.append({"name": "Stability", "points": 10.0, "max": 20, "detail": "Needs at least 7 trading days - neutral score."})

    q = 100.0 if quality_score is None else float(quality_score)
    parts.append({"name": "Data quality", "points": clamp(q / 100) * 20, "max": 20, "detail": f"Cleaning quality score {q:.0f}/100."})

    score = round(sum(p["points"] for p in parts))
    grade = "Strong" if score >= 80 else "Healthy" if score >= 60 else "Watch closely" if score >= 40 else "At risk"
    for p in parts:
        p["points"] = round(p["points"], 1)
    return {"score": score, "grade": grade, "parts": parts}
