import pandas as pd

from src.analytics import kpi, trends


def _df():
    d = pd.DataFrame({"order_date": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-10-01"]),
                      "sales": [100.0, 100.0, 100.0], "profit": [10.0, None, 20.0], "quantity": [1, 1, 1]})
    d["month"] = d["order_date"].dt.to_period("M").astype(str)
    return d


def test_kpis_and_margin_ignore_blank_profit():
    k = kpi.compute_kpis(_df())
    assert k["total_sales"] == 300 and k["total_profit"] == 30 and k["total_orders"] == 3
    assert round(k["profit_margin"], 2) == 15.0              # 30 / 200 (row with blank profit excluded)


def test_compare_periods():
    c = trends.compare_periods(_df(), "profit")
    assert (c["previous"], c["current"]) == (10.0, 20.0) and c["direction"] == "increase" and c["pct"] == 100.0
