"""Period-over-period comparison."""
import pandas as pd

from src.utils import pct_change

METRICS = ("sales", "profit")


def latest_two_months(df: pd.DataFrame):
    months = sorted(df["month"].unique())
    if len(months) < 2:
        raise ValueError("At least two months of data are needed to compare periods.")
    return months[-2], months[-1]


def partial_month_warning(df: pd.DataFrame, previous: str, current: str):
    """Comparing a half-finished month to a full one would be misleading - say so."""
    prev_days = df.loc[df["month"] == previous, "order_date"].dt.date.nunique()
    curr_days = df.loc[df["month"] == current, "order_date"].dt.date.nunique()
    curr_last = df.loc[df["month"] == current, "order_date"].max()
    month_len = pd.Period(current).days_in_month
    if curr_last.day < month_len - 2 or curr_days < 0.8 * prev_days:
        return (f"{current} only has data up to {curr_last.date()} ({curr_days} trading days vs {prev_days} in "
                f"{previous}). A partial month will look like a decline - interpret with care.")
    return None


def compare_periods(df: pd.DataFrame, metric: str = "profit", previous: str | None = None, current: str | None = None):
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {METRICS}")
    if previous is None or current is None:
        previous, current = latest_two_months(df)
    months = set(df["month"].unique())
    if previous not in months or current not in months:
        raise ValueError("Pick two months that exist in this dataset.")
    if previous == current:
        raise ValueError("Pick two different months to compare.")
    prev_v = float(df.loc[df["month"] == previous, metric].sum())
    curr_v = float(df.loc[df["month"] == current, metric].sum())
    delta = curr_v - prev_v
    change = pct_change(prev_v, curr_v)
    direction = "flat" if change is None or abs(change) < 1 else ("increase" if delta > 0 else "decline")
    return {
        "metric": metric, "previous_period": previous, "current_period": current,
        "previous": prev_v, "current": curr_v, "delta": delta, "pct": change, "direction": direction,
        "partial_warning": partial_month_warning(df, previous, current),
    }
