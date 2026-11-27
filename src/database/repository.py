"""Dataset storage. Every dataset belongs to ONE user; all reads/writes are checked against the owner id."""
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from .connection import get_connection

ID_RE = re.compile(r"^[0-9a-f]{10}$")


class DatasetNotFound(KeyError):
    pass


class Repository:
    def __init__(self, processed_dir: Path, report_dir: Path, database_url: str = ""):
        self.dir, self.report_dir, self.database_url = Path(processed_dir), Path(report_dir), database_url
        self.dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    # ---- helpers ----
    def _meta_path(self, ds_id): return self.dir / f"{ds_id}.json"

    def get_meta(self, ds_id: str, owner: int) -> dict:
        """Raises DatasetNotFound for unknown ids AND for datasets that belong to someone else."""
        if not isinstance(ds_id, str) or not ID_RE.match(ds_id) or not self._meta_path(ds_id).exists():
            raise DatasetNotFound(ds_id)
        meta = json.loads(self._meta_path(ds_id).read_text())
        if meta.get("owner") != owner:
            raise DatasetNotFound(ds_id)
        return meta

    def _write_meta(self, meta): self._meta_path(meta["id"]).write_text(json.dumps(meta, default=str))

    # ---- datasets ----
    def save_dataset(self, df: pd.DataFrame, filename: str, quality: dict, owner: int) -> dict:
        ds_id = uuid.uuid4().hex[:10]
        df.to_pickle(self.dir / f"{ds_id}.pkl")
        meta = {"id": ds_id, "owner": owner, "filename": filename, "upload_date": datetime.now().isoformat(timespec="seconds"),
                "row_count": int(len(df)), "quality": quality}
        self._write_meta(meta)
        self._mirror(meta)
        return meta

    def load_dataset(self, ds_id: str, owner: int) -> pd.DataFrame:
        self.get_meta(ds_id, owner)                       # ownership check
        return pd.read_pickle(self.dir / f"{ds_id}.pkl")

    def list_datasets(self, owner: int) -> list[dict]:
        metas = []
        for p in self.dir.glob("*.json"):
            try:
                m = json.loads(p.read_text())
            except ValueError:
                continue
            if m.get("owner") == owner:
                metas.append(m)
        return sorted(metas, key=lambda m: m["upload_date"], reverse=True)

    def delete_dataset(self, ds_id: str, owner: int):
        self.get_meta(ds_id, owner)
        for p in (self.dir / f"{ds_id}.pkl", self._meta_path(ds_id), self.report_dir / f"report_{ds_id}.html"):
            p.unlink(missing_ok=True)

    def delete_user_data(self, owner: int):
        """Remove every dataset (and report) belonging to a user - used when an account is deleted."""
        for m in self.list_datasets(owner):
            self.delete_dataset(m["id"], owner)

    # ---- reports ----
    def save_report(self, ds_id: str, owner: int, html: str) -> Path:
        self.get_meta(ds_id, owner)
        path = self.report_dir / f"report_{ds_id}.html"
        path.write_text(html, encoding="utf-8")
        return path

    def report_path(self, ds_id: str, owner: int) -> Path | None:
        try:
            self.get_meta(ds_id, owner)
        except DatasetNotFound:
            return None
        p = self.report_dir / f"report_{ds_id}.html"
        return p if p.exists() else None

    # ---- optional PostgreSQL mirror (best effort) ----
    def _mirror(self, meta: dict) -> None:
        conn = get_connection(self.database_url)
        if not conn:
            return
        try:
            with conn, conn.cursor() as cur:
                cur.execute("INSERT INTO datasets (filename, upload_date, row_count) VALUES (%s, %s, %s)",
                            (meta["filename"], meta["upload_date"], meta["row_count"]))
        except Exception:
            pass
        finally:
            conn.close()
