from __future__ import annotations

import os
from typing import Any

import httpx

from server.core.imagetools import compute_default_subject_box
from server.models.db import get_templates_for_keyword


def _fallback_analysis_for(image_id: str, upload_index: int = 0) -> dict[str, Any]:
    roles = ["top", "middle", "bottom"]
    role = roles[upload_index % 3]
    return {
        "image_id": image_id,
        "role": role,
        "subject_box": compute_default_subject_box(1080, 720),
        "crop_window": {"x": 0, "y": 0, "w": 1080, "h": 480, "aspect": 2.25},
    }


async def analyze_image(image_id: str, image_path: str, upload_index: int = 0) -> dict[str, Any]:
    ai_base_url = os.getenv("AI_BASE_URL")
    ai_key = os.getenv("AI_API_KEY")
    if not ai_base_url:
        return _fallback_analysis_for(image_id, upload_index)

    try:
        model_name = os.getenv("AI_MODEL", "default")
        payload = {
            "model": model_name,
            "image_id": image_id,
            "path": image_path,
            "index": upload_index,
            "prompt": "Return a normalized subject_box and role in top|middle|bottom format. subject_box = [x, y, w, h] normalized to 0-1."
        }
        headers = {"Authorization": f"Bearer {ai_key}"} if ai_key else {}
        response = httpx.post(f"{ai_base_url.rstrip('/')}/analyze", json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        role = str(data.get("role", ["top", "middle", "bottom"][upload_index % 3])).lower()
        subject_box = data.get("subject_box") or compute_default_subject_box(1080, 720)
        if not isinstance(subject_box, (list, tuple)) or len(subject_box) != 4:
            subject_box = compute_default_subject_box(1080, 720)
        return {
            "image_id": image_id,
            "role": role if role in {"top", "middle", "bottom"} else ["top", "middle", "bottom"][upload_index % 3],
            "subject_box": [float(v) for v in subject_box],
            "crop_window": data.get("crop_window") or {"x": 0, "y": 0, "w": 1080, "h": 480, "aspect": 2.25},
        }
    except Exception:
        return _fallback_analysis_for(image_id, upload_index)


def generate_copy_variants(keyword: str, style_hint: str | None = None) -> list[dict[str, Any]]:
    keyword = (keyword or "").strip() or "风景"
    seeds = get_templates_for_keyword(keyword)
    base_cn = [
        "山谷里，雾气先学会沉默",
        "林间的风沿着水声一路往前走",
        "人终会在回响里找到自己",
    ]
    base_en = [
        "In the valley, the mist learns silence before dawn.",
        "The wind threads through the woods and carries the river's voice onward.",
        "Only when we return to the roots do we hear ourselves.",
    ]

    if seeds:
        first = seeds[0]
        second = seeds[1] if len(seeds) > 1 else seeds[0]
        third = seeds[2] if len(seeds) > 2 else seeds[0]
        base_cn = [
            first["cn_line"],
            second["cn_line"],
            third["cn_line"],
        ]
        base_en = [
            first["en_line"],
            second["en_line"],
            third["en_line"],
        ]

    angle_variants = [
        {
            "id": 1,
            "lines_cn": [
                base_cn[0],
                "风沿着谷地把时间慢慢铺开",
                "人最终回到根下，才听见自己",
            ],
            "lines_en": [
                base_en[0],
                "Wind follows the valley and lets time unfold gradually.",
                "Only returning to the roots do we hear ourselves clearly.",
            ],
            "recommend": True,
        },
        {
            "id": 2,
            "lines_cn": [
                "雾先把地平线藏起来",
                "水声缓慢改写了这片山野",
                "我们终于懂得，归处总在一棵树下",
            ],
            "lines_en": [
                "Mist first hides the horizon from sight.",
                "The river’s voice slowly rewrites the contours of the land.",
                "We learn that refuge is always under a tree.",
            ],
            "recommend": False,
        },
        {
            "id": 3,
            "lines_cn": [
                "白昼在山脊上轻轻落下",
                "日光沿着坡面把故事看见",
                "人从远处走回来，心才有了归处",
            ],
            "lines_en": [
                "Daylight settles lightly on the ridge.",
                "Sunlight traces the slope and reveals the story of the place.",
                "Only when we walk back from afar does the heart find a home.",
            ],
            "recommend": False,
        },
    ]
    return angle_variants
