from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps

from server.core.imagetools import is_supported_file, save_as_jpeg
from server.core.scanner import scan_black_borders
from server.models.db import add_image_record

router = APIRouter(prefix="/api")
logger = logging.getLogger("triptych")


def get_max_upload_mb() -> int:
    try:
        return max(1, int(os.getenv("MAX_UPLOAD_MB", "10")))
    except ValueError:
        return 10


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must include a valid filename.")

    filename = file.filename.lower()
    if filename.endswith((".heic", ".heif")) or (file.content_type or "").lower() in {"image/heic", "image/heif"}:
        raise HTTPException(status_code=422, detail="HEIC images are not supported; please transcode to JPG, PNG, or WebP.")
    if not is_supported_file(file.filename, file.content_type):
        raise HTTPException(status_code=422, detail="Unsupported image format; allowed: JPG, JPEG, PNG, WebP.")

    max_upload_mb = get_max_upload_mb()
    content = await file.read()
    if len(content) > max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_upload_mb}MB upload limit.")

    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        if image.mode in {"RGBA", "LA", "P"}:
            image = image.convert("RGBA")
            white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
            white_bg.paste(image, mask=image.getchannel("A"))
            image = white_bg.convert("RGB")
        elif image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to decode uploaded image: {exc}") from exc

    image_id = uuid.uuid4().hex
    storage_path = Path(__file__).resolve().parents[1] / "data" / "uploads" / f"{image_id}.jpg"
    width, height = save_as_jpeg(image, storage_path)
    black_borders = scan_black_borders(image)
    add_image_record(image_id, str(storage_path), width, height, datetime.utcnow().isoformat(timespec="seconds"))
    logger.info("image uploaded", extra={"image_id": image_id})

    return {
        "image_id": image_id,
        "width": width,
        "height": height,
        "black_borders": black_borders,
    }
