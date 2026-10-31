"""Clean a sales dataset and report every change that was made.

Documented rules (nothing is silently invented):
  * Exact duplicate rows are removed.
  * Rows with an unparseable date or a missing sales value are removed (cannot be placed in time / valued).
  * Missing PROFIT is NOT replaced with zero. The row stays (its sales are real) and profit is left
    blank, so profit totals simply exclude it. The count is reported.
  * Currency symbols and thousands separators (₹ 1,00,000) are stripped before numeric conversion.
  * Text fields are trimmed and standardised to Title Case ("  laptop " -> "Laptop").
  * Negative sales/profit are kept (returns, losses are real) but flagged.
"""
import pandas as pd

from .validator import REQUIRED_COLUMNS

TEXT_COLS = ["product", "category", "region"]
NUM_COLS = ["quantity", "sales", "profit", "discount_pct"]


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = (series.astype(str)
               .str.replace(r"[₹$€£,\s]", "", regex=True)
               .str.replace("%", "", regex=False)
               .replace({"": None, "nan": None, "None": None, "NaN": None, "null": None}))
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="ISO8601")
    retry = parsed.isna() & series.notna()
    if retry.any():
        parsed.loc[retry] = pd.to_datetime(series[retry], errors="coerce", dayfirst=True, format="mixed")
    return parsed


def clean(df: pd.DataFrame):
    """Return (clean_df, report)."""
    df = df.copy()
    report = {"rows_in": int(len(df)), "issues": []}

    def note(kind, count, detail, severity="medium"):
        if count:
            report["issues"].append({"type": kind, "count": int(count), "detail": detail, "severity": severity})

    absent = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if "profit" in absent:
        report["issues"].append({"type": "no_profit_column", "count": 1, "severity": "medium",
                                 "detail": "No profit column was provided, so profit figures show as 0 - choose one when mapping columns to unlock profit analysis."})
    # Fill optional columns so downstream code is uniform
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA if col in NUM_COLS or col == "quantity" else "Unknown"

    # Text standardisation
    changed = 0
    for col in TEXT_COLS:
        original = df[col].astype(str)
        df[col] = original.str.strip().str.title().replace({"": "Unknown", "Nan": "Unknown"})
        changed += int((original != df[col]).sum())
    note("inconsistent_text", changed, "Trimmed whitespace / fixed casing in product, category, region.", "low")

    # Numbers
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = _to_number(df[col])

    # Dates
    df["order_date"] = _parse_dates(df["order_date"])

    # Duplicates (exact)
    dup = df.duplicated(keep="first")
    note("duplicates", dup.sum(), "Exact duplicate rows removed.", "medium")
    df = df[~dup]

    bad_date = df["order_date"].isna()
    note("invalid_dates", bad_date.sum(), "Rows removed: date missing or not a real calendar date.", "high")
    df = df[~bad_date]

    no_sales = df["sales"].isna()
    note("missing_sales", no_sales.sum(), "Rows removed: sales value missing.", "high")
    df = df[~no_sales]

    # Flag only (no deletion / no imputation)
    note("missing_profit", 0 if "profit" in absent else df["profit"].isna().sum(),
         "Kept, but profit left blank (NOT set to 0) - excluded from profit totals.", "medium")
    note("missing_quantity", df["quantity"].isna().sum(), "Kept; units/price analysis ignores these rows.", "low")
    note("negative_values", ((df["sales"] < 0) | (df["profit"] < 0)).sum(),
         "Negative sales/profit kept (returns or loss-making orders) - review manually.", "low")

    df = df.sort_values("order_date").reset_index(drop=True)
    df["month"] = df["order_date"].dt.to_period("M").astype(str)

    report["rows_out"] = int(len(df))
    report["rows_removed"] = report["rows_in"] - report["rows_out"]
    total_issues = sum(i["count"] for i in report["issues"])
    report["quality_score"] = max(0, round(100 - (total_issues / max(report["rows_in"], 1)) * 100, 1))
    report["date_range"] = [str(df["order_date"].min().date()), str(df["order_date"].max().date())] if len(df) else []
    return df, report
