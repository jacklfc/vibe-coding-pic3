from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.core.llm import generate_copy_variants

router = APIRouter(prefix="/api")


class CopyRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    style_hint: str | None = None


@router.post("/copy")
async def create_copy(payload: CopyRequest):
    keyword = payload.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword cannot be blank.")

    variants = generate_copy_variants(keyword, payload.style_hint)
    if len(variants) < 3:
        raise HTTPException(status_code=502, detail="Failed to create enough copy variants.")

    # Only one recommendation is true; keep it deterministic.
    for index, item in enumerate(variants):
        item["recommend"] = index == 0

    return {"sets": variants[:3]}
