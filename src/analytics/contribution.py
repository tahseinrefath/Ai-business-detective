"""Contribution analysis: WHO moved the number, and WHAT moved inside them.

Important: a contributor is where the change happened - it is evidence, not proof of the cause.
"""
import pandas as pd

from src.utils import pct_change


def rank_contributors(df, previous, current, metric="profit", by="category", total_delta=None, top=None):
    """Rank segments of `by` by how much they contributed to the total change.

    share_of_change = segment_delta / total_delta * 100
    (positive when the segment moved in the same direction as the total).
    """
    pv = df[df["month"] == previous].groupby(by)[metric].sum()
    cv = df[df["month"] == current].groupby(by)[metric].sum()
    t = pd.concat([pv.rename("previous"), cv.rename("current")], axis=1).fillna(0.0)
    t["delta"] = t["current"] - t["previous"]
    if total_delta is None:
        total_delta = t["delta"].sum()
    t["pct"] = [pct_change(a, b) for a, b in zip(t["previous"], t["current"])]
    t["share_of_change"] = (t["delta"] / total_delta * 100) if total_delta else 0.0
    # Biggest movers in the direction of the overall change come first
    t = t.sort_values("delta", ascending=(total_delta < 0))
    if top:
        t = t.head(top)
    out = t.reset_index()
    first = out.columns[0]
    out = out.rename(columns={first: "name"})
    out["name"] = out["name"].astype(str)
    return out.to_dict("records")


def rank_segments(df, previous, current, metric="profit", total_delta=None, top=5):
    """Product x Region combinations - often pinpoints the real culprit."""
    d = df.copy()
    d["segment"] = d["product"] + " · " + d["region"]
    return rank_contributors(d, previous, current, metric, "segment", total_delta, top)


def driver_breakdown(df, previous, current, product=None, region=None, category=None):
    """Inside one segment, compare orders, units, avg selling price, margin, discount."""
    seg = df
    label = []
    for col, val in (("product", product), ("region", region), ("category", category)):
        if val:
            seg = seg[seg[col] == val]
            label.append(val)

    def stats(month):
        m = seg[seg["month"] == month]
        orders = int(len(m))
        units = float(m["quantity"].sum(skipna=True))
        sales = float(m["sales"].sum())
        has_p = m["profit"].notna()
        profit = float(m["profit"].sum(skipna=True))
        base = float(m.loc[has_p, "sales"].sum())
        out = {
            "orders": orders, "units": units, "sales": sales, "profit": profit,
            "avg_selling_price": (sales / units) if units else None,
            "margin": (profit / base * 100) if base else None,
            "avg_discount": float(m["discount_pct"].mean()) if "discount_pct" in m and m["discount_pct"].notna().any() else None,
        }
        return out

    prev, curr = stats(previous), stats(current)
    changes = []
    for key, text in (("orders", "Order count"), ("units", "Units sold"), ("avg_selling_price", "Avg selling price"),
                      ("margin", "Profit margin"), ("avg_discount", "Avg discount")):
        a, b = prev[key], curr[key]
        if a is None or b is None:
            continue
        is_ratio = key in ("margin", "avg_discount")
        change = (b - a) if is_ratio else pct_change(a, b)
        if change is None:                      # no baseline to compare against (e.g. 0 orders last month)
            continue
        changes.append({"driver": key, "label": text, "previous": a, "current": b,
                        "change": change, "unit": "pts" if is_ratio else "%"})
    return {"segment": " · ".join(label) or "All data", "previous": prev, "current": curr, "changes": changes}
