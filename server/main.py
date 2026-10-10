from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api.analyze import router as analyze_router
from server.api.compose import router as compose_router
from server.api.copy import router as copy_router
from server.api.upload import router as upload_router
from server.models.db import cleanup_expired_uploads, ensure_runtime_dirs, init_db

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"
UPLOADS_DIR = DATA_DIR / "uploads"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("job_id", "image_id", "removed"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


logger = logging.getLogger("triptych")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

ensure_runtime_dirs()
init_db()

app = FastAPI(title="Triptych Film Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_runtime_dirs()
    init_db()
    ttl_hours = get_env_int("UPLOAD_TTL_HOURS", 24)
    cleanup_expired_uploads(ttl_hours)
    asyncio.create_task(cleanup_loop())


async def cleanup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        ttl_hours = get_env_int("UPLOAD_TTL_HOURS", 24)
        removed = cleanup_expired_uploads(ttl_hours)
        logger.info("upload cleanup completed", extra={"removed": removed})


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    logger.info("health check requested")
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "bad_request",
        404: "image_not_found",
        413: "payload_too_large",
        422: "unsupported_format",
        502: "upstream_ai_failure",
        504: "timeout",
    }
    error_code = code_map.get(exc.status_code, "internal_error")
    return JSONResponse(status_code=exc.status_code, content={"error": error_code, "message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "bad_request", "message": exc.errors()})


app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(copy_router)
app.include_router(compose_router)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
