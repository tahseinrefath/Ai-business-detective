"""What-if lab: a transparent 'back of the envelope' scenario on ONE product x region segment.

Assumptions (stated in the UI): average order value and profit margin stay constant unless you change them.
It is an illustration of sensitivity, not a forecast.
"""
import pandas as pd

LIMITS = {"order_change_pct": (-100, 500), "price_change_pct": (-50, 100), "margin_change_pts": (-30, 30)}


def clamp(name, v):
    lo, hi = LIMITS[name]
    return max(lo, min(hi, float(v)))


def list_segments(df: pd.DataFrame, current: str, previous: str) -> list[dict]:
    d = df.assign(segment=df["product"] + " · " + df["region"])
    cur = d[d["month"] == current].groupby("segment").agg(orders=("sales", "size"), sales=("sales", "sum"), profit=("profit", "sum"))
    prev = d[d["month"] == previous].groupby("segment").size().rename("prev_orders")
    t = cur.join(prev, how="left").fillna({"prev_orders": 0}).sort_values("sales", ascending=False)
    return [{"name": n, **{k: float(v) for k, v in r.items()}} for n, r in t.iterrows()]


def baseline(df: pd.DataFrame, month: str, segment: str) -> dict:
    product, region = segment.split(" · ")
    m = df[(df["month"] == month) & (df["product"] == product) & (df["region"] == region)]
    if m.empty:
        raise ValueError("No data for that segment in the latest month.")
    sales = float(m["sales"].sum())
    return {"orders": int(len(m)), "sales": sales, "profit": float(m["profit"].sum()),
            "margin": (float(m["profit"].sum()) / sales * 100) if sales else 0.0,
            "month_total_profit": float(df.loc[df["month"] == month, "profit"].sum())}


def simulate(base: dict, order_change_pct=0, price_change_pct=0, margin_change_pts=0) -> dict:
    oc, pc, mp = (clamp("order_change_pct", order_change_pct), clamp("price_change_pct", price_change_pct),
                  clamp("margin_change_pts", margin_change_pts))
    orders = base["orders"] * (1 + oc / 100)
    aov = (base["sales"] / base["orders"]) * (1 + pc / 100) if base["orders"] else 0.0
    sales = orders * aov
    margin = base["margin"] + mp
    profit = sales * margin / 100
    delta = profit - base["profit"]
    total = base["month_total_profit"]
    return {"inputs": {"order_change_pct": oc, "price_change_pct": pc, "margin_change_pts": mp},
            "scenario": {"orders": orders, "sales": sales, "profit": profit, "margin": margin},
            "delta_sales": sales - base["sales"], "delta_profit": delta,
            "pct_of_month_profit": (delta / total * 100) if total else None}
