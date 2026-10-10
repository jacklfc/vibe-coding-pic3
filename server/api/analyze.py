from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.core.imagetools import compute_crop_window, compute_default_subject_box
from server.core.llm import analyze_image
from server.models.db import get_analysis_result, get_image_record, save_analysis_result

router = APIRouter(prefix="/api")
logger = logging.getLogger("triptych")


class AnalyzeRequest(BaseModel):
    image_ids: list[str] = Field(..., min_length=1)


async def _analyze_single(image_id: str, index: int) -> dict[str, Any]:
    record = get_image_record(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Image {image_id} does not exist.")

    fallback_role = ["top", "middle", "bottom"][index % 3]
    try:
        analysis = await analyze_image(image_id, record["path"], index)
        role = analysis.get("role") or fallback_role
        subject_box = analysis.get("subject_box") or compute_default_subject_box(record["width"], record["height"])
        crop_window = analysis.get("crop_window") or compute_crop_window(subject_box, record["width"], record["height"], aspect=2.25)
    except Exception:
        subject_box = compute_default_subject_box(record["width"], record["height"])
        role = fallback_role
        crop_window = compute_crop_window(subject_box, record["width"], record["height"], aspect=2.25)

    if role not in {"top", "middle", "bottom"}:
        role = fallback_role
    crop_window = compute_crop_window(subject_box, record["width"], record["height"], aspect=2.25)
    save_analysis_result(image_id, role, subject_box, crop_window)
    logger.info("image analyzed", extra={"image_id": image_id, "role": role})
    return {"image_id": image_id, "role": role, "subject_box": subject_box, "crop_window": crop_window}


@router.post("/analyze")
async def analyze_images(payload: AnalyzeRequest):
    if not payload.image_ids:
        raise HTTPException(status_code=400, detail="image_ids must not be empty.")
    try:
        results = await asyncio.gather(*[_analyze_single(image_id, index) for index, image_id in enumerate(payload.image_ids)])
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Upstream AI analysis failed: {exc}") from exc

    ordered_ids = [item["image_id"] for item in sorted(results, key=lambda item: {"top": 0, "middle": 1, "bottom": 2}[item["role"]])]
    return {"images": results, "ordered_ids": ordered_ids}
