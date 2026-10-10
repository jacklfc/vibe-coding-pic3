from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from server.core.fonts import load_font

SEGMENT_HEIGHT = 480
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440


def ensure_1080x480(image: Image.Image) -> Image.Image:
    if image.size == (1080, 480):
        return image
    return image.resize((1080, 480), Image.Resampling.LANCZOS)


def build_triptych(images: Iterable[Image.Image], lines_cn: list[str], lines_en: list[str], text_shadow: bool = True, film_grain: bool = False) -> Image.Image:
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "black")
    images = list(images)
    if len(images) != 3:
        raise ValueError("Triptych requires exactly 3 images")
    if len(lines_cn) != 3 or len(lines_en) != 3:
        raise ValueError("Copy text must provide three segments")

    for idx, image in enumerate(images):
        segment = ensure_1080x480(image)
        y = idx * SEGMENT_HEIGHT
        canvas.paste(segment, (0, y))
        draw_segment_text(canvas, idx, lines_cn[idx], lines_en[idx], text_shadow=text_shadow)

    if film_grain:
        canvas = add_film_grain(canvas)
    return canvas


def add_film_grain(image: Image.Image) -> Image.Image:
    noisy = image.copy().convert("RGBA")
    alpha = Image.new("L", image.size, 0)
    for x in range(image.width):
        for y in range(image.height):
            alpha.putpixel((x, y), 10)
    return noisy


def draw_segment_text(base: Image.Image, index: int, cn_line: str, en_line: str, text_shadow: bool = True) -> None:
    segment_top = index * SEGMENT_HEIGHT
    draw = ImageDraw.Draw(base)
    cn_font = load_font(30, index=2)
    en_font = load_font(22, index=2)

    cn_left = (base.width - draw.textbbox((0, 0), cn_line, font=cn_font)[2]) / 2
    en_left = (base.width - draw.textbbox((0, 0), en_line, font=en_font)[2]) / 2
    cn_top = segment_top + int(SEGMENT_HEIGHT * 0.84)
    en_top = cn_top + 30 + 10

    if text_shadow:
        shadow_color = (0, 0, 0)
        draw.text((cn_left + 1, cn_top + 1), cn_line, font=cn_font, fill=shadow_color)
        draw.text((en_left + 1, en_top + 1), en_line, font=en_font, fill=shadow_color)

    draw.text((cn_left, cn_top), cn_line, font=cn_font, fill=(255, 255, 255))
    draw.text((en_left, en_top), en_line, font=en_font, fill=(255, 255, 255))
