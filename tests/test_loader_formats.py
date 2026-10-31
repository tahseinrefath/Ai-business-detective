"""Every supported format is generated on the fly, loaded, cleaned and checked."""
import json

import pandas as pd
import pytest

from src.data_processing import cleaner, loader, validator

ROWS = [["2026-09-01", "Laptop", "Electronics", "South", 2, 100000, 10000],
        ["2026-09-02", "Mobile", "Electronics", "North", 3, 60000, 9000],
        ["2026-10-01", "Laptop", "Electronics", "South", 1, 50000, 3000],
        ["2026-10-03", "Headphones", "Accessories", "West", 4, 8000, 1500]]
COLS = ["order_date", "product", "category", "region", "quantity", "sales", "profit"]


def _check(path):
    df, note = loader.load_with_info(path)
    validator.validate_columns(df)
    clean, rep = cleaner.clean(df)
    assert len(clean) == 4 and clean["sales"].sum() == 218000 and note
    return note


def test_csv_tsv_txt_json(tmp_path):
    base = pd.DataFrame(ROWS, columns=COLS)
    base.to_csv(tmp_path / "a.csv", index=False); _check(tmp_path / "a.csv")
    base.to_csv(tmp_path / "a.tsv", index=False, sep="\t"); _check(tmp_path / "a.tsv")
    base.to_csv(tmp_path / "a.txt", index=False, sep=";"); _check(tmp_path / "a.txt")
    base.to_json(tmp_path / "a.json", orient="records"); _check(tmp_path / "a.json")
    (tmp_path / "b.json").write_text(json.dumps({"meta": 1, "data": base.to_dict("records")})); _check(tmp_path / "b.json")


def test_excel_with_title_rows_and_many_sheets(tmp_path):
    p = tmp_path / "report.xlsx"
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"Notes": ["ignore me"]}).to_excel(w, sheet_name="Readme", index=False)
        top = pd.DataFrame([["ACME Retail - Q3 Sales"], [None], [None]] )
        top.to_excel(w, sheet_name="Sales", index=False, header=False)
        pd.DataFrame(ROWS, columns=["Date", "Item", "Category", "City", "Qty", "Revenue", "Profit"]).to_excel(
            w, sheet_name="Sales", index=False, startrow=3)          # header on row 4, aliases used
    note = _check(p)
    assert "Sales" in note and "of 2" in note


def test_ods(tmp_path):
    p = tmp_path / "a.ods"
    pd.DataFrame(ROWS, columns=COLS).to_excel(p, engine="odf", index=False)
    _check(p)


def _make_pdf(path, chunks):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import PageBreak, SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    story = []
    for i, chunk in enumerate(chunks):
        t = Table([COLS] + chunk if i == 0 else chunk)               # later pages: no header (continuation)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
        story += [t, PageBreak()]
    SimpleDocTemplate(str(path), pagesize=A4).build(story)


def test_pdf_table_across_pages(tmp_path):
    p = tmp_path / "sales.pdf"
    _make_pdf(p, [ROWS[:2], ROWS[2:]])
    note = _check(p)
    assert "PDF" in note


def test_pdf_without_table_gives_friendly_error(tmp_path):
    from reportlab.pdfgen import canvas
    p = tmp_path / "text.pdf"; c = canvas.Canvas(str(p)); c.drawString(100, 750, "Just a paragraph, no table."); c.save()
    with pytest.raises(ValueError, match="No sales table"):
        loader.load_with_info(p)


def test_pbix_errors_are_friendly(tmp_path):
    p = tmp_path / "broken.pbix"; p.write_bytes(b"not a real pbix")
    with pytest.raises(ValueError, match="Power BI|pbixray"):
        loader.load_with_info(p)


def test_unsupported_type(tmp_path):
    p = tmp_path / "x.exe"; p.write_bytes(b"x")
    with pytest.raises(ValueError, match="Unsupported"):
        loader.load_with_info(p)
