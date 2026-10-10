from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Light.ttc",
]


def get_font_path() -> str:
    for candidate in DEFAULT_FONT_PATHS:
        if Path(candidate).exists():
            return candidate
    return "DejaVuSans.ttf"


def load_font(size: int, index: int = 2) -> ImageFont.FreeTypeFont:
    font_path = get_font_path()
    candidates = []
    if Path(font_path).suffix.lower() == ".ttc":
        candidates = [
            (font_path, index),
            (font_path, 0),
            ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
            ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
        ]
    else:
        candidates = [(font_path, None)]

    for path, font_index in candidates:
        if not path or not Path(path).exists():
            continue
        try:
            if font_index is None:
                return ImageFont.truetype(path, size=size)
            return ImageFont.truetype(path, size=size, index=font_index)
        except Exception:
            continue

    return ImageFont.truetype("DejaVuSans.ttf", size=size)
