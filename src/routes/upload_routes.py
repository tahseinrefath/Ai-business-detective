import re
import time
import uuid
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request

from src import gamify

from src.data_processing import cleaner, loader, validator
from src.utils import jsonable

bp = Blueprint("upload", __name__)
TOKEN = re.compile(r"^[0-9a-f]{32}$")


def _purge_old_temp_files(folder: Path, max_age=3600):
    for p in folder.glob("*"):
        if p.name != ".gitkeep" and p.is_file() and time.time() - p.stat().st_mtime > max_age:
            p.unlink(missing_ok=True)


def _store(df, display_name, note):
    clean_df, quality = cleaner.clean(df)
    if clean_df.empty:
        raise validator.ValidationError("No usable rows remained after cleaning (check date and sales values).")
    meta = current_app.repo.save_dataset(clean_df, display_name, quality, g.user["id"])
    gamify.record(g.user["id"], "upload")
    return jsonify(jsonable({"dataset": meta, "months": sorted(clean_df["month"].unique()), "source_note": note}))


def _ingest(path: Path, display_name: str, allow_mapping=False):
    """Returns (response, keep_file). If columns are not recognised, offer the mapping step."""
    raw, note = loader.load_raw(path)
    df = loader.normalize_columns(raw)
    try:
        validator.validate_columns(df)
    except validator.ValidationError as exc:
        if not allow_mapping or df.empty:
            raise
        preview = raw.head(5).astype(str).to_dict("records")
        resp = jsonify(jsonable({
            "error": str(exc), "needs_mapping": True, "token": path.stem, "filename": display_name,
            "columns": [str(c) for c in raw.columns], "preview": preview,
            "suggestions": loader.suggest_mapping(raw), "source_note": note}))
        return (resp, 422), True
    return _store(df, display_name, note), False


@bp.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="No file selected."), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return jsonify(error="Unsupported file type. Upload CSV, Excel, JSON, PDF or Power BI (.pbix)."), 400
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    _purge_old_temp_files(folder)
    dest = folder / f"{uuid.uuid4().hex}.{ext}"
    f.save(dest)
    keep = False
    try:
        resp, keep = _ingest(dest, f.filename, allow_mapping=True)
        return resp
    except (validator.ValidationError, ValueError) as e:
        return jsonify(error=str(e)), 422
    except Exception:
        current_app.logger.exception("upload failed")
        return jsonify(error="Could not read that file. Check it is a valid, uncorrupted file."), 400
    finally:
        if not keep:
            dest.unlink(missing_ok=True)


@bp.post("/api/upload/map")
def upload_mapped():
    """Second step: the user tells us which column is which."""
    body = request.get_json(silent=True) or {}
    token, mapping = str(body.get("token", "")), body.get("mapping") or {}
    if not TOKEN.match(token):
        return jsonify(error="Invalid upload token - please upload the file again."), 400
    matches = list(Path(current_app.config["UPLOAD_FOLDER"]).glob(f"{token}.*"))
    if not matches:
        return jsonify(error="That upload expired - please upload the file again."), 404
    path = matches[0]
    try:
        raw, note = loader.load_raw(path)
        chosen = {t: c for t, c in mapping.items() if t in loader.TARGETS and c}
        missing = [t for t in loader.REQUIRED_TARGETS if t not in chosen]
        if missing:
            return jsonify(error=f"Please choose a column for: {', '.join(missing)}."), 422
        if len(set(chosen.values())) != len(chosen):
            return jsonify(error="Each column can only be used once."), 422
        if any(c not in raw.columns for c in chosen.values()):
            return jsonify(error="One of the chosen columns does not exist in the file."), 422
        df = raw[list(chosen.values())].rename(columns={c: t for t, c in chosen.items()})
        resp = _store(df, str(body.get("filename") or path.name), note + " · columns mapped manually")
        path.unlink(missing_ok=True)          # only once it worked; user mistakes above keep the file so they can retry
        return resp
    except (validator.ValidationError, ValueError) as e:
        return jsonify(error=str(e)), 422


@bp.post("/api/sample")
def sample():
    kind = (request.get_json(silent=True) or {}).get("kind", "clean")
    name = {"clean": "sample_sales.csv", "dirty": "sample_sales_dirty.csv"}.get(kind)
    if not name:
        return jsonify(error="Unknown sample."), 400
    try:
        resp, _ = _ingest(Path(current_app.config["SAMPLE_FOLDER"]) / name, name)
        return resp
    except (validator.ValidationError, ValueError) as e:
        return jsonify(error=str(e)), 422


@bp.get("/api/datasets")
def datasets():
    return jsonify(jsonable(current_app.repo.list_datasets(g.user["id"])))
