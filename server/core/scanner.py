from __future__ import annotations

from typing import Iterable

from PIL import Image


def _is_dark(pixel: Iterable[int]) -> bool:
    r, g, b = pixel[:3]
    return (r + g + b) / 3 <= 40


def scan_black_borders(image: Image.Image) -> dict[str, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()

    top = 0
    for y in range(height):
        row_dark = 0
        for x in range(width):
            if _is_dark(pixels[x, y]):
                row_dark += 1
        if row_dark / max(width, 1) > 0.85:
            top = y + 1
        else:
            break

    bottom = 0
    for y in range(height - 1, -1, -1):
        row_dark = 0
        for x in range(width):
            if _is_dark(pixels[x, y]):
                row_dark += 1
        if row_dark / max(width, 1) > 0.85:
            bottom = height - y
        else:
            break

    left = 0
    for x in range(width):
        col_dark = 0
        for y in range(height):
            if _is_dark(pixels[x, y]):
                col_dark += 1
        if col_dark / max(height, 1) > 0.85:
            left = x + 1
        else:
            break

    right = 0
    for x in range(width - 1, -1, -1):
        col_dark = 0
        for y in range(height):
            if _is_dark(pixels[x, y]):
                col_dark += 1
        if col_dark / max(height, 1) > 0.85:
            right = width - x
        else:
            break

    return {"top": max(0, top), "bottom": max(0, bottom), "left": max(0, left), "right": max(0, right)}
