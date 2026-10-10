from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def is_supported_file(filename: str, content_type: str | None = None) -> bool:
    suffix = Path(filename).suffix.lower()
    if suffix in {".heic", ".heif"}:
        return False
    if suffix in ALLOWED_EXTS:
        return True
    if content_type:
        return content_type.lower().split(";")[0] in {"image/jpeg", "image/png", "image/webp"}
    return False


def normalize_image_orientation(image: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(image)


def save_as_jpeg(image: Image.Image, output_path: str | Path) -> tuple[int, int]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgb = normalize_image_orientation(image).convert("RGB")
    rgb.save(output_path, format="JPEG", quality=95)
    return rgb.size


def compute_default_subject_box(width: int, height: int) -> list[float]:
    x = 0.25
    y = 0.22
    w = 0.5
    h = 0.55
    return [round(x, 4), round(y, 4), round(w, 4), round(h, 4)]


def compute_crop_window(subject_box: list[float], width: int, height: int, aspect: float = 2.25) -> dict[str, float | int]:
    if not isinstance(subject_box, (list, tuple)) or len(subject_box) != 4:
        subject_box = compute_default_subject_box(width, height)

    x, y, w, h = [float(v) for v in subject_box]
    center_x = x + w / 2.0
    center_y = y + h / 2.0

    crop_w = width / aspect
    crop_h = height / (aspect / 1.0)
    crop_w = min(width, crop_w)
    crop_h = min(height, crop_h)

    win_w = crop_w
    win_h = win_w / aspect
    if win_h > height:
        win_h = height
        win_w = win_h * aspect

    crop_x = center_x * width - win_w / 2.0
    crop_y = center_y * height - win_h / 2.0
    crop_x = max(0.0, min(width - win_w, crop_x))
    crop_y = max(0.0, min(height - win_h, crop_y))

    if crop_x + win_w > width:
        crop_x = max(0.0, width - win_w)
    if crop_y + win_h > height:
        crop_y = max(0.0, height - win_h)

    # fallback if crop is empty or no good fit
    if win_w <= 0 or win_h <= 0 or crop_w <= 0:
        win_w = min(width, height * aspect)
        win_h = win_w / aspect
        crop_x = (width - win_w) / 2.0
        crop_y = (height - win_h) / 2.0

    return {
        "x": int(round(crop_x)),
        "y": int(round(crop_y)),
        "w": int(round(win_w)),
        "h": int(round(win_h)),
        "aspect": round(aspect, 2),
    }


def crop_region(image: Image.Image, crop_window: dict[str, Any], target_size: tuple[int, int] | None = None) -> Image.Image:
    x = max(0, int(crop_window.get("x", 0)))
    y = max(0, int(crop_window.get("y", 0)))
    w = max(1, int(crop_window.get("w", image.width)))
    h = max(1, int(crop_window.get("h", image.height)))
    x2 = min(image.width, x + w)
    y2 = min(image.height, y + h)
    if x2 <= x or y2 <= y:
        x = max(0, (image.width - min(image.width, image.height * 2.25)) // 2)
        y = max(0, (image.height - min(image.width / 2.25, image.height)) // 2)
        x2 = min(image.width, x + min(image.width, int(image.height * 2.25)))
        y2 = min(image.height, y + int(image.height))
    crop = image.crop((x, y, x2, y2))
    if target_size:
        crop = crop.resize(target_size, Image.Resampling.LANCZOS)
    return crop


def center_crop_2_25(image: Image.Image, target_size: tuple[int, int] = (1080, 480)) -> Image.Image:
    width, height = image.size
    target_ratio = target_size[0] / target_size[1]
    if width / height > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        crop = image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        crop = image.crop((0, top, width, top + new_height))
    crop = crop.resize(target_size, Image.Resampling.LANCZOS)
    return crop


def build_segment_from_window(image: Image.Image, crop_window: dict[str, Any], target_size: tuple[int, int] = (1080, 480)) -> Image.Image:
    if crop_window:
        return crop_region(image, crop_window, target_size)
    return center_crop_2_25(image, target_size)


def draw_text_block(base: Image.Image, cn_line: str, en_line: str, segment_top: int, segment_height: int = 480, text_shadow: bool = True) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(base)
    block_top = int(segment_top + segment_height * 0.84)
    block_bottom = int(segment_top + segment_height * 0.97)
    text_block_y = block_top
    cn_size = 30
    en_size = 22
    margin = 14
    line_gap = 10

    cn_font = __import__("server.core.fonts", fromlist=["load_font"]).load_font(cn_size, index=2)
    en_font = __import__("server.core.fonts", fromlist=["load_font"]).load_font(en_size, index=2)
    cn_bbox = draw.textbbox((0, 0), cn_line, font=cn_font)
    en_bbox = draw.textbbox((0, 0), en_line, font=en_font)

    cn_w = cn_bbox[2] - cn_bbox[0]
    en_w = en_bbox[2] - en_bbox[0]
    x_cn = (base.width - cn_w) / 2
    x_en = (base.width - en_w) / 2
    y_cn = text_block_y
    y_en = y_cn + cn_size + line_gap

    if text_shadow:
        shadow_rgb = (0, 0, 0)
        draw.text((x_cn + 1, y_cn + 1), cn_line, font=cn_font, fill=shadow_rgb)
        draw.text((x_en + 1, y_en + 1), en_line, font=en_font, fill=shadow_rgb)
        draw.text((x_cn + 2, y_cn + 2), cn_line, font=cn_font, fill=shadow_rgb)
        draw.text((x_en + 2, y_en + 2), en_line, font=en_font, fill=shadow_rgb)

    draw.text((x_cn, y_cn), cn_line, font=cn_font, fill=(255, 255, 255))
    draw.text((x_en, y_en), en_line, font=en_font, fill=(255, 255, 255))
    return None
