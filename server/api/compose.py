from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from PIL import Image

from server.core.imagetools import build_segment_from_window, center_crop_2_25
from server.core.llm import generate_copy_variants
from server.core.triptych import build_triptych
from server.models.db import add_history_record, get_analysis_result, get_image_record

router = APIRouter(prefix="/api")
logger = logging.getLogger("triptych")


class ComposeRequest(BaseModel):
    job_id: str | None = None
    image_ids: list[str] = Field(..., min_length=3, max_length=3)
    copy_set_id: int = Field(default=1, ge=1, le=3)
    use_analyze_crop: bool = True
    film_grain: bool = False
    text_shadow: bool = True
    keyword: str | None = None


@router.post("/compose")
async def compose_images(payload: ComposeRequest):
    if len(payload.image_ids) != 3:
        raise HTTPException(status_code=400, detail="Exactly three image_ids are required.")

    images_by_id: dict[str, Image.Image] = {}
    ordered: list[tuple[int, str]] = []
    role_order = {"top": 0, "middle": 1, "bottom": 2}

    for idx, image_id in enumerate(payload.image_ids):
        record = get_image_record(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Image {image_id} does not exist.")
        image = Image.open(record["path"])
        analysis = get_analysis_result(image_id)
        role = "top"
        if analysis is not None and analysis.get("role") in role_order:
            role = analysis["role"]
        elif idx == 0:
            role = "top"
        elif idx == 1:
            role = "middle"
        else:
            role = "bottom"
        ordered.append((role_order.get(role, idx), image_id))
        images_by_id[image_id] = image

    ordered.sort(key=lambda item: item[0])
    segments: list[Image.Image] = []

    for segment_index, (_, image_id) in enumerate(ordered):
        image = images_by_id[image_id]
        analysis = get_analysis_result(image_id)
        crop_window = None
        if payload.use_analyze_crop and analysis:
            crop_window = analysis.get("crop_window")
        if crop_window:
            segment = build_segment_from_window(image, crop_window, target_size=(1080, 480))
        else:
            segment = center_crop_2_25(image, (1080, 480))
        segments.append(segment)

    keyword = payload.keyword or "风景"
    copy_sets = generate_copy_variants(keyword)
    selected = next((item for item in copy_sets if int(item["id"]) == int(payload.copy_set_id)), copy_sets[0])
    lines_cn = selected["lines_cn"]
    lines_en = selected["lines_en"]

    canvas = build_triptych(segments, lines_cn, lines_en, text_shadow=payload.text_shadow, film_grain=payload.film_grain)

    job_id = payload.job_id or str(uuid4())
    result_dir = Path(__file__).resolve().parents[1] / "data" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{job_id}.jpg"
    canvas.save(result_path, format="JPEG", quality=95)

    add_history_record(job_id, keyword, payload.copy_set_id, str(result_path))
    logger.info("composition generated", extra={"job_id": job_id, "keyword": keyword})

    return {
        "job_id": job_id,
        "result_url": f"/results/{job_id}.jpg",
        "canvas": {"width": 1080, "height": 1440},
    }
