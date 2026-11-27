import pytest

def test_pages_render(client):
    for p in ("/", "/dashboard", "/investigation", "/reports", "/lab", "/profile"):
        assert client.get(p).status_code == 200


def test_full_flow(client):
    r = client.post("/api/sample", json={"kind": "dirty"})
    assert r.status_code == 200
    ds = r.json["dataset"]["id"]
    assert client.get(f"/api/dashboard?dataset={ds}").json["kpis"]["total_orders"] > 0
    a = client.post("/api/ask", json={"dataset": ds, "question": "Why did profit decrease?"})
    assert a.status_code == 200 and a.json["explanation"]["source"] == "rules"
    assert client.post(f"/api/report/{ds}").status_code == 200
    assert b"AI Business Detective" in client.get(f"/api/report/{ds}").data


def test_errors(client):
    assert client.post("/api/upload").status_code == 400
    assert client.get("/api/dashboard?dataset=nope").status_code == 404
    assert client.post("/api/ask", json={"dataset": "x", "question": ""}).status_code == 400


def test_filters_preview_exports_and_month_picker(client):
    ds = client.post("/api/sample", json={"kind": "clean"}).json["dataset"]["id"]
    d = client.get(f"/api/dashboard?dataset={ds}&region=South").json
    assert d["filtered_rows"] < d["meta"]["row_count"] and d["forecast"]["next_month"] == "2026-11"
    assert client.get(f"/api/dashboard?dataset={ds}&region=Mars").status_code == 422
    p = client.get(f"/api/preview?dataset={ds}&q=laptop&sort=sales&size=5").json
    assert len(p["rows"]) == 5 and all(r["product"] == "Laptop" for r in p["rows"])
    assert client.get(f"/api/export/{ds}/clean.csv").data.startswith(b"order_date")
    assert b"Laptop" in client.get(f"/api/export/{ds}/contributors.csv").data
    ok = client.post("/api/ask", json={"dataset": ds, "question": "why", "previous": "2026-08", "current": "2026-09", "metric": "sales"})
    assert ok.status_code == 200 and ok.json["investigation"]["comparison"]["current_period"] == "2026-09"
    assert client.post("/api/ask", json={"dataset": ds, "question": "why", "previous": "2026-09", "current": "2026-09"}).status_code == 422
    assert client.get("/data").status_code == 200


def test_upload_excel_and_rejects_bad_type(client, tmp_path):
    import io
    import pandas as pd
    buf = io.BytesIO()
    pd.DataFrame([["2026-09-01", "Laptop", "Electronics", "South", 1, 50000, 5000],
                  ["2026-10-01", "Laptop", "Electronics", "South", 1, 40000, 3000]],
                 columns=["order_date", "product", "category", "region", "quantity", "sales", "profit"]).to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/api/upload", data={"file": (buf, "sales.xlsx")}, content_type="multipart/form-data")
    assert r.status_code == 200 and "Excel" not in r.json.get("error", "") and r.json["source_note"]
    bad = client.post("/api/upload", data={"file": (io.BytesIO(b"x"), "evil.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400


def test_unrecognised_headers_offer_mapping_then_work(client):
    import io
    csv = ("Txn Day,Total Bill,Item Name,Shop City,Units,Margin Amt\n"
           "2026-09-01,\"₹1,000\",Pen,Chennai,1,100\n2026-09-02,2000,Book,Delhi,2,200\n"
           "2026-10-01,1500,Pen,Chennai,1,150\n2026-10-02,900,Book,Delhi,1,60\n")
    r = client.post("/api/upload", data={"file": (io.BytesIO(csv.encode()), "shop.csv")}, content_type="multipart/form-data")
    assert r.status_code == 422 and r.json["needs_mapping"]
    sug = r.json["suggestions"]
    assert sug["order_date"] == "Txn Day" and sug["sales"] == "Total Bill" and sug["region"] == "Shop City"
    # missing required choice and bad token are rejected
    assert client.post("/api/upload/map", json={"token": r.json["token"], "mapping": {"sales": "Total Bill"}}).status_code == 422
    assert client.post("/api/upload/map", json={"token": "../../etc/passwd", "mapping": {}}).status_code == 400
    ok = client.post("/api/upload/map", json={"token": r.json["token"], "filename": "shop.csv", "mapping": sug})
    assert ok.status_code == 200 and ok.json["dataset"]["row_count"] == 4
    ds = ok.json["dataset"]["id"]
    assert client.get(f"/api/dashboard?dataset={ds}").json["kpis"]["total_sales"] == 5400
    # token is single-use
    assert client.post("/api/upload/map", json={"token": r.json["token"], "mapping": sug}).status_code == 404


def test_mapping_without_profit_column_still_works(client):
    import io
    csv = "when,amount_paid\n2026-09-01,100\n2026-09-05,300\n2026-10-02,200\n"
    r = client.post("/api/upload", data={"file": (io.BytesIO(csv.encode()), "min.csv")}, content_type="multipart/form-data")
    assert r.status_code == 422 and r.json["needs_mapping"]
    ok = client.post("/api/upload/map", json={"token": r.json["token"], "mapping": {"order_date": "when", "sales": "amount_paid"}})
    assert ok.status_code == 200
    assert any(i["type"] == "no_profit_column" for i in ok.json["dataset"]["quality"]["issues"])
    ds = ok.json["dataset"]["id"]
    assert client.get(f"/api/dashboard?dataset={ds}").status_code == 200
    assert client.post(f"/api/report/{ds}").status_code == 200       # report must not crash when margin is unknown
