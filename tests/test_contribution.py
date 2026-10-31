"""Known-answer test: the sample data has a planted decline in Laptop · South."""
from pathlib import Path

import pytest

from src.analytics.investigation import investigate
from src.data_processing import cleaner, loader

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample" / "sample_sales.csv"


@pytest.fixture(scope="module")
def inv():
    df, _ = cleaner.clean(loader.load_file(SAMPLE))
    return investigate(df, "profit")


def test_profit_declines(inv):
    assert inv["comparison"]["direction"] == "decline" and inv["comparison"]["pct"] < -10


def test_planted_culprit_found(inv):
    assert inv["contributors"]["segment"][0]["name"] == "Laptop · South"
    assert inv["contributors"]["region"][0]["name"] == "South"


def test_drivers_show_orders_down_discount_up(inv):
    by = {d["driver"]: d for d in inv["drivers"]["changes"]}
    assert by["orders"]["change"] < -40 and by["avg_discount"]["change"] > 5


def test_planted_anomalies_flagged(inv):
    assert "2026-09-21" in {a["date"] for a in inv["anomalies"]}
