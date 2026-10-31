"""Dashboard filters (region / category / product / date range). 'All' or blank means no filter."""
import pandas as pd


def _active(v):
    return v not in (None, "", "All", "all")


def apply_filters(df: pd.DataFrame, region=None, category=None, product=None, start=None, end=None) -> pd.DataFrame:
    out = df
    for col, val in (("region", region), ("category", category), ("product", product)):
        if _active(val):
            out = out[out[col] == val]
    if _active(start):
        out = out[out["order_date"] >= pd.to_datetime(start, errors="coerce")]
    if _active(end):
        out = out[out["order_date"] <= pd.to_datetime(end, errors="coerce") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
    return out


def filter_options(df: pd.DataFrame) -> dict:
    return {
        "regions": sorted(df["region"].unique().tolist()), "categories": sorted(df["category"].unique().tolist()),
        "products": sorted(df["product"].unique().tolist()), "months": sorted(df["month"].unique().tolist()),
        "min_date": str(df["order_date"].min().date()), "max_date": str(df["order_date"].max().date()),
    }
