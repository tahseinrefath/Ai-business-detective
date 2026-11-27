"""Core KPI calculations. All business maths lives here, not in route handlers."""
import pandas as pd

from src.utils import pct_change


def compute_kpis(df: pd.DataFrame) -> dict:
    sales = float(df["sales"].sum())
    profit = float(df["profit"].sum(skipna=True))
    # Margin uses only rows that HAVE a profit value, so blank profits don't drag it down.
    has_profit = df["profit"].notna()
    base = float(df.loc[has_profit, "sales"].sum())
    orders = int(len(df))
    return {
        "total_sales": sales,
        "total_profit": profit,
        "profit_margin": (profit / base * 100) if base else None,
        "total_orders": orders,
        "units_sold": float(df["quantity"].sum(skipna=True)),
        "avg_order_value": sales / orders if orders else None,
    }


def monthly_summary(df: pd.DataFrame) -> list[dict]:
    g = df.groupby("month").agg(sales=("sales", "sum"), profit=("profit", "sum"),
                                orders=("sales", "size"), days=("order_date", lambda s: s.dt.date.nunique()))
    g["margin"] = g["profit"] / g["sales"] * 100
    g["sales_change"] = [None] + [pct_change(a, b) for a, b in zip(g["sales"][:-1], g["sales"][1:])]
    g["profit_change"] = [None] + [pct_change(a, b) for a, b in zip(g["profit"][:-1], g["profit"][1:])]
    return g.reset_index().to_dict("records")


def group_summary(df: pd.DataFrame, by: str, limit: int | None = None) -> list[dict]:
    g = df.groupby(by).agg(sales=("sales", "sum"), profit=("profit", "sum"), orders=("sales", "size"))
    g["margin"] = g["profit"] / g["sales"] * 100
    g = g.sort_values("profit", ascending=False)
    if limit:
        g = g.head(limit)
    return g.reset_index().rename(columns={by: "name"}).to_dict("records")


def daily_series(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df["order_date"].dt.date).agg(sales=("sales", "sum"), profit=("profit", "sum"),
                                                 orders=("sales", "size"))
    return [{"date": str(d), **row} for d, row in g.to_dict("index").items()]
