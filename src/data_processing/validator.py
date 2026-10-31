"""Check that an uploaded dataset has what the analysis needs."""
import pandas as pd

REQUIRED_COLUMNS = ["order_date", "product", "category", "region", "quantity", "sales", "profit"]
MINIMUM_COLUMNS = ["order_date", "sales"]  # absolute minimum to do anything useful


class ValidationError(ValueError):
    """Raised when a dataset cannot be analysed."""


def validate_columns(df: pd.DataFrame) -> dict:
    """Return {'missing_required', 'missing_optional'}; raise if the minimum is absent."""
    missing_min = [c for c in MINIMUM_COLUMNS if c not in df.columns]
    if missing_min:
        raise ValidationError(
            f"Missing required column(s): {', '.join(missing_min)}. "
            f"Expected columns: {', '.join(REQUIRED_COLUMNS)} (optional: discount_pct)."
        )
    if df.empty:
        raise ValidationError("The file contains no rows.")
    return {"missing_optional": [c for c in REQUIRED_COLUMNS if c not in df.columns]}
