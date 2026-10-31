"""Generate sample datasets with a KNOWN, planted change.

Planted story (used by the tests):
  * Oct 2026 profit falls versus Sep 2026.
  * The main culprit is Laptop sales in the South region:
    fewer orders, heavier discounts and a thinner margin.
  * Sep 21 has an unusual bulk Headphones order (anomaly); Oct 12 is an unusually quiet day.

Run:  python scripts/generate_sample_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "sample"
rng = np.random.default_rng(42)

PRODUCTS = {  # product: (category, unit price, base margin)
    "Laptop": ("Electronics", 50000, 0.11),
    "Mobile": ("Electronics", 20000, 0.15),
    "Tablet": ("Electronics", 30000, 0.12),
    "Smartwatch": ("Accessories", 8000, 0.18),
    "Headphones": ("Accessories", 2500, 0.24),
}
REGIONS = ["North", "South", "East", "West"]


def build() -> pd.DataFrame:
    rows = []
    for day in pd.date_range("2026-08-01", "2026-10-31"):
        n_orders = int(rng.integers(9, 15))
        for _ in range(n_orders):
            product = rng.choice(list(PRODUCTS), p=[0.18, 0.28, 0.14, 0.15, 0.25])
            region = rng.choice(REGIONS, p=[0.27, 0.30, 0.20, 0.23])
            category, price, margin = PRODUCTS[product]
            discount = float(rng.uniform(0.0, 0.06))
            is_oct = day.month == 10

            if is_oct and product == "Laptop" and region == "South":
                if rng.random() < 0.70:       # far fewer laptop orders in the South
                    continue
                discount = float(rng.uniform(0.12, 0.18))
                margin -= 0.06

            qty = int(rng.integers(1, 4))
            sales = price * qty * (1 - discount) * float(rng.normal(1, 0.03))
            profit = sales * (margin - discount * 0.4) * float(rng.normal(1, 0.08))
            rows.append([day.date().isoformat(), product, category, region, qty,
                         round(sales), round(profit), round(discount * 100, 1)])

    df = pd.DataFrame(rows, columns=["order_date", "product", "category", "region",
                                     "quantity", "sales", "profit", "discount_pct"])

    # Anomaly 1: unusual bulk order on 21 Sep (not an error - a real spike)
    bulk = pd.DataFrame([["2026-09-21", "Headphones", "Accessories", "East", 150, 357000, 85000, 5.0]],
                        columns=df.columns)
    df = pd.concat([df, bulk], ignore_index=True)
    # Anomaly 2: unusually quiet day on 12 Oct
    df = df[~((df.order_date == "2026-10-12") & (rng.random(len(df)) < 0.85))]
    return df.sort_values("order_date").reset_index(drop=True)


def make_dirty(clean: pd.DataFrame) -> pd.DataFrame:
    """Same story, but with realistic data-quality problems for the cleaner to find."""
    d = clean[clean.order_date >= "2026-09-01"].sample(260, random_state=7).sort_values("order_date").copy()
    d = d.reset_index(drop=True)
    d["order_date"] = d["order_date"].astype(object)
    d["sales"] = d["sales"].astype(object)
    d["profit"] = d["profit"].astype(object)
    d.loc[::9, "order_date"] = pd.to_datetime(d.loc[::9, "order_date"]).dt.strftime("%d-%m-%Y")
    d.loc[[5, 40, 91], "order_date"] = ["Invalid", "31-02-2026", "not a date"]
    d.loc[[12, 33, 77, 120, 160], "profit"] = None
    d.loc[[20], "sales"] = None
    d.loc[::13, "sales"] = d.loc[::13, "sales"].map(lambda v: f"₹{int(v):,}" if v is not None and v == v else v)
    d.loc[[8, 60], "product"] = ["laptop ", "MOBILE"]
    d.loc[[15, 70], "region"] = [" south", "NORTH"]
    d = pd.concat([d, d.iloc[[3, 3, 25, 50, 50, 99]]], ignore_index=True)  # exact duplicates
    return d.sample(frac=1, random_state=1).reset_index(drop=True)


if __name__ == "__main__":
    clean = build()
    clean.to_csv(OUT / "sample_sales.csv", index=False)
    make_dirty(clean).to_csv(OUT / "sample_sales_dirty.csv", index=False)
    print(f"sample_sales.csv: {len(clean)} rows | sample_sales_dirty.csv written")
