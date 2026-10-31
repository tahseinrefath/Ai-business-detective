"""Flag unusual days / months.

Two complementary, explainable methods:
  1. Robust z-score on daily sales (median + MAD) - works on small data.
  2. IsolationForest (scikit-learn) on daily [sales, profit, orders] when there are enough days.

An anomaly is NOT automatically an error or a problem: it can be a festival, a bulk order,
a stock-out or a data-entry mistake. The output says "unusual", never "wrong".
"""
import numpy as np
import pandas as pd


def _daily(df):
    g = df.groupby(df["order_date"].dt.normalize()).agg(sales=("sales", "sum"), profit=("profit", "sum"),
                                                        orders=("sales", "size"))
    return g.reset_index().rename(columns={"order_date": "date"})


def detect_daily_anomalies(df, z_threshold=3.5, contamination=0.03, max_results=8):
    d = _daily(df)
    if len(d) < 7:
        return []
    med = d["sales"].median()
    mad = (d["sales"] - med).abs().median() or 1.0
    d["robust_z"] = 0.6745 * (d["sales"] - med) / mad
    d["flag_z"] = d["robust_z"].abs() >= z_threshold
    d["flag_if"] = False
    if len(d) >= 30:
        try:
            from sklearn.ensemble import IsolationForest
            X = d[["sales", "profit", "orders"]].fillna(0.0).to_numpy()
            d["flag_if"] = IsolationForest(contamination=contamination, random_state=42).fit_predict(X) == -1
        except Exception:  # sklearn missing / failed -> z-score alone is still valid
            pass
    flagged = d[d["flag_z"] | (d["flag_if"] & (d["robust_z"].abs() >= 2.5))].copy()
    flagged["abs_z"] = flagged["robust_z"].abs()
    flagged = flagged.sort_values("abs_z", ascending=False).head(max_results)
    out = []
    for _, r in flagged.iterrows():
        high = r["sales"] > med
        out.append({
            "date": str(r["date"].date()), "sales": float(r["sales"]), "profit": float(r["profit"]),
            "orders": int(r["orders"]), "typical_daily_sales": float(med),
            "direction": "spike" if high else "dip", "score": round(float(r["abs_z"]), 1),
            "methods": [m for m, f in (("robust z-score", r["flag_z"]), ("isolation forest", r["flag_if"])) if f],
            "note": ("Unusually high - check for bulk orders, promotions or duplicated entries."
                     if high else "Unusually low - check for stock-outs, outages, holidays or missing data."),
        })
    return sorted(out, key=lambda x: x["date"])


def detect_monthly_shifts(monthly: list[dict], threshold=10.0):
    """Flag month-over-month changes beyond +/- threshold %."""
    out = []
    for row in monthly:
        for key in ("sales_change", "profit_change"):
            v = row.get(key)
            if v is not None and abs(v) >= threshold:
                out.append({"month": row["month"], "metric": key.split("_")[0], "change_pct": float(v)})
    return out
