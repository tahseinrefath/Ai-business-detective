"""Load many file types into one DataFrame with canonical column names.

Supported: CSV, TSV, TXT, Excel (.xlsx .xlsm .xls), OpenDocument (.ods), JSON,
PDF (tables with a text layer) and Power BI (.pbix, best effort).

Messy real-world files are handled: Excel title rows above the header, several sheets
(the one that best matches the expected columns is used) and tables split across PDF pages.
"""
from pathlib import Path

import pandas as pd

ALIASES = {
    "date": "order_date", "orderdate": "order_date", "order date": "order_date", "invoice_date": "order_date",
    "revenue": "sales", "sale": "sales", "amount": "sales", "total_sales": "sales", "sales_amount": "sales",
    "profit_amount": "profit", "net_profit": "profit",
    "qty": "quantity", "units": "quantity",
    "item": "product", "product_name": "product", "sub_category": "product",
    "segment": "category", "product_category": "category",
    "city": "region", "state": "region", "zone": "region",
    "discount": "discount_pct", "discount_percent": "discount_pct",
    "transaction_date": "order_date", "sale_date": "order_date", "sales_date": "order_date", "bill_date": "order_date",
    "date_of_sale": "order_date", "order_dt": "order_date", "purchase_date": "order_date",
    "net_sales": "sales", "total": "sales", "total_amount": "sales", "sales_value": "sales", "turnover": "sales",
    "gross_profit": "profit", "net_income": "profit", "earnings": "profit",
    "quantity_sold": "quantity", "no_of_units": "quantity",
    "sub-category": "product", "item_name": "product", "sku": "product",
    "branch": "region", "area": "region", "store": "region", "location": "region",
}
KNOWN = {"order_date", "product", "category", "region", "quantity", "sales", "profit", "discount_pct"}
EXTENSIONS = {"csv", "tsv", "txt", "xlsx", "xlsm", "xls", "ods", "json", "pdf", "pbix"}
SPREADSHEET = {"xlsx", "xlsm", "xls", "ods"}


def _canon(name) -> str:
    c = str(name).strip().lower()
    c = "_".join(c.replace("-", " ").split())
    return ALIASES.get(c, ALIASES.get(c.replace("_", " "), c))


TARGETS = ["order_date", "sales", "profit", "product", "category", "region", "quantity", "discount_pct"]
REQUIRED_TARGETS = ["order_date", "sales"]
_HINTS = {
    "order_date": ("date", "day", "time", "dt"), "sales": ("sale", "revenue", "amount", "total", "turnover", "value", "price"),
    "profit": ("profit", "margin", "income", "earning"), "product": ("product", "item", "sku", "name", "title"),
    "category": ("categ", "type", "segment", "dept", "group", "class"), "region": ("region", "city", "state", "zone", "area", "branch", "store", "location", "country"),
    "quantity": ("qty", "quant", "unit", "count", "pieces"), "discount_pct": ("discount", "disc"),
}


def suggest_mapping(raw: pd.DataFrame) -> dict:
    """Best guess of which source column plays which role (the user confirms/edits it)."""
    used, out = set(), {}
    numeric = {c for c in raw.columns if pd.to_numeric(raw[c].astype(str).str.replace(r"[₹$€£,\s%]", "", regex=True), errors="coerce").notna().mean() > 0.8}
    for target in TARGETS:
        best, best_score = None, 0
        for c in raw.columns:
            if c in used:
                continue
            name = str(c).lower()
            score = sum(1 for h in _HINTS[target] if h in name)
            if target == "order_date" and score == 0 and pd.to_datetime(raw[c].astype(str).head(30), errors="coerce", format="mixed").notna().mean() > 0.8 and c not in numeric:
                score = 1
            if target in ("sales", "profit", "quantity", "discount_pct") and c not in numeric:
                score = 0
            if score > best_score:
                best, best_score = c, score
        out[target] = best
        if best is not None:
            used.add(best)
    return out


def _unique(cols) -> list[str]:
    seen, out = {}, []
    for c in cols:
        c = str(c).strip() or "unnamed"
        seen[c] = seen.get(c, 0) + 1
        out.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    return out


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_canon(c) for c in df.columns]
    return df.loc[:, ~df.columns.duplicated()]


def _score(df: pd.DataFrame) -> int:
    """How many expected columns a table has (used to pick the right sheet / table)."""
    return len(KNOWN & {_canon(c) for c in df.columns})


def _promote_header(raw: pd.DataFrame) -> pd.DataFrame:
    """Find the real header row (skips title/blank rows above it) and use it as the column names."""
    best_i, best = 0, -1
    for i in range(min(len(raw), 15)):
        n = len(KNOWN & {_canon(v) for v in raw.iloc[i].dropna()})
        if n > best:
            best_i, best = i, n
    df = raw.iloc[best_i + 1:].copy()
    df.columns = [str(v) if pd.notna(v) else f"unnamed_{j}" for j, v in enumerate(raw.iloc[best_i])]
    return df.dropna(how="all").reset_index(drop=True)


def _read_spreadsheet(path: Path):
    sheets = pd.read_excel(path, sheet_name=None, header=None)   # every sheet, raw
    if not sheets:
        raise ValueError("The workbook has no sheets.")
    candidates = {name: _promote_header(raw) for name, raw in sheets.items() if not raw.dropna(how="all").empty}
    if not candidates:
        raise ValueError("All sheets in the workbook are empty.")
    name = max(candidates, key=lambda n: _score(candidates[n]))
    note = f"Used sheet '{name}'" + (f" (of {len(sheets)})" if len(sheets) > 1 else "")
    return candidates[name], note


def _read_pdf(path: Path):
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("Reading PDFs needs the 'pdfplumber' package: pip install pdfplumber")
    frames, header, pages_with_tables = [], None, 0
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page in pdf.pages[:60]:                                  # safety cap
            tables = page.extract_tables()
            pages_with_tables += bool(tables)
            for t in tables:
                rows = [[(c or "").strip() for c in r] for r in t if r and any((c or "").strip() for c in r)]
                if len(rows) < 2:
                    continue
                raw = pd.DataFrame(rows)
                if header is None:
                    df = _promote_header(raw)
                    if _score(df) >= 2:
                        header, frames = list(df.columns), [df]
                elif raw.shape[1] == len(header):                    # continuation on a later page
                    body = raw
                    if [_canon(v) for v in raw.iloc[0]] == [_canon(h) for h in header]:
                        body = raw.iloc[1:]                          # repeated header row
                    body = body.copy(); body.columns = header
                    frames.append(body)
    if not frames:
        raise ValueError("No sales table found in this PDF. PDFs must contain real text tables (not scanned images). "
                         "Try exporting the table to CSV/Excel instead.")
    return pd.concat(frames, ignore_index=True), f"Read {len(pd.concat(frames))} table rows from {pages_with_tables} of {n_pages} PDF page(s)"


def _read_pbix(path: Path):
    try:
        from pbixray import PBIXRay
        from pbixray import LiveConnectionError, NoEmbeddedModelError
    except ImportError:
        raise ValueError("Reading Power BI files needs the 'pbixray' package: pip install pbixray. "
                         "Alternatively, in Power BI use Export data (…) → .csv, or copy the table to Excel.")
    try:
        model = PBIXRay(str(path))
        tables = list(model.tables)
    except LiveConnectionError:
        raise ValueError("This .pbix is a live connection - it holds no data. Export the data to CSV/Excel from Power BI instead.")
    except NoEmbeddedModelError:
        raise ValueError("This .pbix has no embedded data model (likely DirectQuery). Export the table to CSV/Excel instead.")
    except Exception:
        raise ValueError("Could not read this Power BI file. Export the table to CSV/Excel from Power BI instead.")
    best, best_name = None, None
    for t in tables:
        try:
            df = model.get_table(t)
        except Exception:
            continue
        if best is None or _score(df) > _score(best):
            best, best_name = df, t
    if best is None or _score(best) == 0:
        raise ValueError(f"No table in this Power BI file looks like sales data. Tables found: {', '.join(map(str, tables)) or 'none'}. "
                         "Rename columns to order_date / product / region / sales / profit, or export a table to CSV.")
    return best, f"Used Power BI table '{best_name}' (of {len(tables)})"


def _read_json(path: Path):
    import json
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except ValueError:                                              # maybe JSON Lines (one object per line)
        return pd.read_json(path, lines=True), "Read JSON Lines"
    if isinstance(data, dict):
        records = next((v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], dict)), None)
        data = records if records is not None else data             # {"data":[...]} wrapper, else column-oriented dict
    if isinstance(data, list):
        return pd.json_normalize(data), "Read JSON records"
    return pd.DataFrame(data), "Read JSON (column-oriented)"


def load_with_info(path):
    """Return (DataFrame with canonical columns, human-readable note about what was read)."""
    raw, note = load_raw(path)
    return normalize_columns(raw), note


def load_raw(path):
    """Like load_with_info but keeps the file's ORIGINAL column names (used by the column-mapping step)."""
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")
    if ext in ("csv", "tsv", "txt"):
        try:
            df = pd.read_csv(path, sep=None if ext != "csv" else ",", engine="python" if ext != "csv" else "c")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=None if ext != "csv" else ",", engine="python" if ext != "csv" else "c", encoding="latin-1")
        note = f"Read {ext.upper()} file"
    elif ext in SPREADSHEET:
        df, note = _read_spreadsheet(path)
    elif ext == "json":
        df, note = _read_json(path)
    elif ext == "pdf":
        df, note = _read_pdf(path)
    elif ext == "pbix":
        df, note = _read_pbix(path)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Supported: {', '.join(sorted(EXTENSIONS))}")
    df = df.copy(); df.columns = _unique(df.columns)
    return df, note


def load_file(path) -> pd.DataFrame:
    return load_with_info(path)[0]
