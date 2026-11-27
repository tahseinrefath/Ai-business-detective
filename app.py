"""AI Business Detective - FastAPI entry point.
Run locally:  python app.py   or   uvicorn app:app --reload --port 5000
OpenAPI docs: http://127.0.0.1:5000/docs  |  OpenAPI JSON: http://127.0.0.1:5000/openapi.json
"""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config import Config
from src.auth import routes as auth_routes
from src.auth.security import create_templates, install_security
from src.database.db import init_db
from src.database.repository import Repository
from src.schemas import ErrorResponse
from src.routes import (
    dashboard_routes,
    data_routes,
    features_routes,
    investigation_routes,
    report_routes,
    upload_routes,
)


def create_app(config_class=Config) -> FastAPI:
    app = FastAPI(
        title="AI Business Detective API",
        version="6.0.0",
        description="Evidence-first business analytics API (FastAPI + Pandas + scikit-learn).",
    )
    app.state.config = config_class

    for key in ("UPLOAD_FOLDER", "PROCESSED_FOLDER", "REPORT_FOLDER", "AVATAR_FOLDER"):
        Path(getattr(config_class, key)).mkdir(parents=True, exist_ok=True)

    app.state.repo = Repository(
        Path(config_class.PROCESSED_FOLDER),
        Path(config_class.REPORT_FOLDER),
        config_class.DATABASE_URL,
    )
    app.state.templates = create_templates(Path(config_class.BASE_DIR) / "templates")

    init_db(app)
    install_security(app)
    # Added after install_security so SessionMiddleware wraps outermost and populates request.session
    app.add_middleware(
        SessionMiddleware,
        secret_key=config_class.SECRET_KEY,
        session_cookie="session",
        max_age=config_class.PERMANENT_SESSION_LIFETIME,
        same_site=str(getattr(config_class, "SESSION_COOKIE_SAMESITE", "Lax")).lower(),
        https_only=bool(getattr(config_class, "SESSION_COOKIE_SECURE", False)),
        path="/",
    )

    @app.exception_handler(HTTPException)
    async def http_exc_handler(_request: Request, exc: HTTPException):
        content = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(_request: Request, _exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": "Invalid request payload."})

    app.mount("/static", StaticFiles(directory=str(Path(config_class.BASE_DIR) / "static")), name="static")

    for r in (
        auth_routes.router,
        features_routes.router,
        dashboard_routes.router,
        data_routes.router,
        upload_routes.router,
        investigation_routes.router,
        report_routes.router,
    ):
        app.include_router(r)

    log_dir = Path(config_class.BASE_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(log_dir / "app.log"), level=logging.INFO)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        # Align 422 OpenAPI schema with our RequestValidationError handler ({"error": "..."})
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["ErrorResponse"] = ErrorResponse.model_json_schema()
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)
        for path_item in schema.get("paths", {}).values():
            for op in path_item.values():
                if isinstance(op, dict):
                    resps = op.get("responses", {})
                    if "422" in resps:
                        resps["422"] = {
                            "description": "Validation Error",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        }
                    # Drop placeholder application/json when an explicit non-JSON media type is declared
                    r200 = resps.get("200", {}).get("content", {})
                    if any(mt != "application/json" for mt in r200):
                        r200.pop("application/json", None)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
