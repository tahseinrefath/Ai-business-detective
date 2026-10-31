"""Orchestrates the 'detective' workflow into one evidence package."""
from . import anomaly_detection as ad
from . import contribution as cont
from . import kpi, trends
from src.utils import pct_change


def _severity(pct):
    if pct is None:
        return "low"
    a = abs(pct)
    return "high" if a >= 20 else "medium" if a >= 8 else "low"


def investigate(df, metric="profit", previous=None, current=None):
    comp = trends.compare_periods(df, metric, previous, current)
    prev, curr, delta = comp["previous_period"], comp["current_period"], comp["delta"]

    contributors = {
        "category": cont.rank_contributors(df, prev, curr, metric, "category", delta, top=5),
        "product": cont.rank_contributors(df, prev, curr, metric, "product", delta, top=5),
        "region": cont.rank_contributors(df, prev, curr, metric, "region", delta, top=5),
        "segment": cont.rank_segments(df, prev, curr, metric, delta, top=5),
    }

    # Drill into the single biggest product x region contributor
    drivers = None
    top_seg = contributors["segment"][0] if contributors["segment"] else None
    if top_seg:
        product, region = top_seg["name"].split(" · ")
        drivers = cont.driver_breakdown(df, prev, curr, product=product, region=region)

    kpi_changes = {}
    for m in ("sales", "profit"):
        a = float(df.loc[df["month"] == prev, m].sum()); b = float(df.loc[df["month"] == curr, m].sum())
        kpi_changes[m] = {"previous": a, "current": b, "pct": pct_change(a, b)}
    oa = int((df["month"] == prev).sum()); ob = int((df["month"] == curr).sum())
    kpi_changes["orders"] = {"previous": oa, "current": ob, "pct": pct_change(oa, ob)}

    monthly = kpi.monthly_summary(df)
    return {
        "metric": metric, "comparison": comp, "severity": _severity(comp["pct"]),
        "contributors": contributors, "drivers": drivers, "kpi_changes": kpi_changes,
        "anomalies": ad.detect_daily_anomalies(df), "monthly_shifts": ad.detect_monthly_shifts(monthly),
    }
