import pandas as pd
import pytest

from src.analytics import extras, kpi
from src.analytics.filters import apply_filters, filter_options
from src.data_processing import cleaner, loader
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample" / "sample_sales.csv"


@pytest.fixture(scope="module")
def df():
    return cleaner.clean(loader.load_file(SAMPLE))[0]


def test_filters(df):
    assert set(apply_filters(df, region="South")["region"]) == {"South"}
    assert len(apply_filters(df, region="All")) == len(df)
    sep = apply_filters(df, start="2026-09-01", end="2026-09-30")
    assert set(sep["month"]) == {"2026-09"}
    assert apply_filters(df, region="Nowhere").empty
    assert "2026-10" in filter_options(df)["months"]


def test_forecast_needs_three_months_and_extends_trend():
    rows = [{"month": f"2026-0{i}", "sales": 100.0 * i, "profit": 10.0 * i} for i in (1, 2, 3)]
    f = extras.forecast_next_month(rows)
    assert f["next_month"] == "2026-04" and round(f["sales"]["projected"]) == 400
    assert extras.forecast_next_month(rows[:2]) is None


def test_discount_bands_and_heatmap(df):
    bands = extras.discount_bands(df)
    assert bands and {"band", "margin", "orders"} <= set(bands[0])
    hm = extras.heatmap(df)
    assert len(hm["z"]) == len(hm["regions"]) and len(hm["z"][0]) == len(hm["products"])
    assert extras.business_pulse(df, kpi.monthly_summary(df))
