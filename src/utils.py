"""Small shared helpers (formatting + JSON-safe conversion)."""
import math

import numpy as np
import pandas as pd


def inr(value) -> str:
    """Format a number as Indian rupees with lakh/crore grouping: 1234567 -> ₹12,34,567."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    sign = "-" if value < 0 else ""
    s = str(int(round(abs(value))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{sign}₹{s}"


def pct(value, digits=1):
    return "n/a" if value is None else f"{value:+.{digits}f}%"


def pct_change(previous, current):
    """Percentage change; None when the base is zero/missing."""
    if previous is None or previous == 0 or pd.isna(previous):
        return None
    return float((current - previous) / abs(previous) * 100)


def jsonable(obj):
    """Recursively convert numpy / pandas objects to plain Python for jsonify."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (math.isnan(obj) or math.isinf(obj)) else float(obj)
    if isinstance(obj, (pd.Timestamp, pd.Period)):
        return str(obj)
    if obj is pd.NaT:
        return None
    return obj
