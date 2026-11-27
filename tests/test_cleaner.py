import pandas as pd

from src.data_processing import cleaner, loader, validator


def _dirty():
    return pd.DataFrame({
        "Order Date": ["2026-09-01", "2026-09-01", "Invalid", "02-09-2026", "2026-09-03"],
        "Product": ["Laptop", "Laptop", "Mobile", " mobile ", "Tablet"],
        "category": ["Electronics"] * 5, "region": ["South", "South", "North", "NORTH", "West"],
        "qty": [1, 1, 2, 2, 1], "Revenue": ["₹50,000", "₹50,000", "20000", "20000", None],
        "profit": [5000, 5000, 3000, None, 900]})


def test_cleaning_rules():
    df = loader.load_file.__globals__["normalize_columns"](_dirty())
    validator.validate_columns(df)
    out, rep = cleaner.clean(df)
    kinds = {i["type"]: i["count"] for i in rep["issues"]}
    assert kinds["duplicates"] == 1 and kinds["invalid_dates"] == 1 and kinds["missing_sales"] == 1
    assert out["sales"].iloc[0] == 50000                      # currency symbol stripped
    assert out["profit"].isna().sum() == 1                    # missing profit NOT turned into 0
    assert set(out["product"]) == {"Laptop", "Mobile"}        # text standardised
    assert out.loc[out["order_date"] == "2026-09-02", "region"].iloc[0] == "North"  # dd-mm-yyyy parsed


def test_missing_columns_rejected():
    import pytest
    with pytest.raises(validator.ValidationError):
        validator.validate_columns(pd.DataFrame({"foo": [1]}))
