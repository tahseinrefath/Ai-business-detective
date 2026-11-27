import logging
from pathlib import Path
import re
import time
import uuid

from fastapi import APIRouter, Body, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse

from src import gamify
from src.auth.security import require_user
from src.data_processing import cleaner, loader, validator
from src.schemas import ColumnMappingRequest, SampleRequest
from src.utils import jsonable

router = APIRouter(tags=["upload"])
TOKEN = re.compile(r"^[0-9a-f]{32}$")
logger = logging.getLogger(__name__)


def _purge_old_temp_files(folder: Path, max_age=3600):
    for p in folder.glob("*"):
        if p.name != ".gitkeep" and p.is_file() and time.time() - p.stat().st_mtime > max_age:
            p.unlink(missing_ok=True)


def _store(repo, uid: int, df, display_name: str, note: str) -> dict:
    clean_df, quality = cleaner.clean(df)
    if clean_df.empty:
        raise validator.ValidationError("No usable rows remained after cleaning (check date and sales values).")
    meta = repo.save_dataset(clean_df, display_name, quality, uid)
    gamify.record(uid, "upload")
    return jsonable({"dataset": meta, "months": sorted(clean_df["month"].unique()), "source_note": note})


def _ingest(repo, uid: int, path: Path, display_name: str, allow_mapping=False):
    """Returns (response, keep_file). If columns are not recognised, offer the mapping step."""
    raw, note = loader.load_raw(path)
    df = loader.normalize_columns(raw)
    try:
        validator.validate_columns(df)
    except validator.ValidationError as exc:
        if not allow_mapping or df.empty:
            raise
        preview = raw.head(5).astype(str).to_dict("records")
        payload = jsonable({
            "error": str(exc),
            "needs_mapping": True,
            "token": path.stem,
            "filename": display_name,
            "columns": [str(c) for c in raw.columns],
            "preview": preview,
            "suggestions": loader.suggest_mapping(raw),
            "source_note": note,
        })
        return JSONResponse(payload, status_code=422), True
    return _store(repo, uid, df, display_name, note), False


@router.post("/api/upload")
async def upload(request: Request, file: UploadFile | None = File(default=None), user=Depends(require_user)):
    if not file or not file.filename:
        return JSONResponse({"error": "No file selected."}, status_code=400)
    cfg = request.app.state.config
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in cfg.ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": "Unsupported file type. Upload CSV, Excel, JSON, PDF or Power BI (.pbix)."},
            status_code=400,
        )
    max_bytes = int(cfg.MAX_CONTENT_LENGTH)
    raw_bytes = await file.read(max_bytes + 1)
    if len(raw_bytes) > max_bytes:
        return JSONResponse({"error": "File too large (max 50 MB)."}, status_code=413)

    folder = Path(cfg.UPLOAD_FOLDER)
    folder.mkdir(parents=True, exist_ok=True)
    _purge_old_temp_files(folder)
    dest = folder / f"{uuid.uuid4().hex}.{ext}"
    dest.write_bytes(raw_bytes)
    keep = False
    try:
        resp, keep = _ingest(request.app.state.repo, user["id"], dest, file.filename, allow_mapping=True)
        return resp
    except (validator.ValidationError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    except Exception:
        logger.exception("upload failed")
        return JSONResponse({"error": "Could not read that file. Check it is a valid, uncorrupted file."}, status_code=400)
    finally:
        if not keep:
            dest.unlink(missing_ok=True)


@router.post("/api/upload/map")
def upload_mapped(
    request: Request,
    body: ColumnMappingRequest = Body(default_factory=ColumnMappingRequest),
    user=Depends(require_user),
):
    """Second step: the user tells us which column is which."""
    token = str(body.token or "")
    mapping = body.mapping or {}
    if not TOKEN.match(token):
        return JSONResponse({"error": "Invalid upload token - please upload the file again."}, status_code=400)
    cfg = request.app.state.config
    matches = list(Path(cfg.UPLOAD_FOLDER).glob(f"{token}.*"))
    if not matches:
        return JSONResponse({"error": "That upload expired - please upload the file again."}, status_code=404)
    path = matches[0]
    try:
        raw, note = loader.load_raw(path)
        chosen = {t: c for t, c in mapping.items() if t in loader.TARGETS and c}
        missing = [t for t in loader.REQUIRED_TARGETS if t not in chosen]
        if missing:
            return JSONResponse({"error": f"Please choose a column for: {', '.join(missing)}."}, status_code=422)
        if len(set(chosen.values())) != len(chosen):
            return JSONResponse({"error": "Each column can only be used once."}, status_code=422)
        if any(c not in raw.columns for c in chosen.values()):
            return JSONResponse({"error": "One of the chosen columns does not exist in the file."}, status_code=422)
        df = raw[list(chosen.values())].rename(columns={c: t for t, c in chosen.items()})
        resp = _store(
            request.app.state.repo,
            user["id"],
            df,
            str(body.filename or path.name),
            note + " · columns mapped manually",
        )
        path.unlink(missing_ok=True)          # only once it worked; user mistakes above keep the file so they can retry
        return resp
    except (validator.ValidationError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@router.post("/api/sample")
def sample(
    request: Request,
    body: SampleRequest = Body(default_factory=SampleRequest),
    user=Depends(require_user),
):
    name = {"clean": "sample_sales.csv", "dirty": "sample_sales_dirty.csv"}.get(body.kind)
    if not name:
        return JSONResponse({"error": "Unknown sample."}, status_code=400)
    try:
        resp, _ = _ingest(
            request.app.state.repo,
            user["id"],
            Path(request.app.state.config.SAMPLE_FOLDER) / name,
            name,
        )
        return resp
    except (validator.ValidationError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@router.get("/api/datasets")
def datasets(request: Request, user=Depends(require_user)):
    return jsonable(request.app.state.repo.list_datasets(user["id"]))
