from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
DB_PATH = DATA_DIR / "templates.db"

TEMPLATE_SEEDS = [
    {"keyword": "雪山", "scene_tag": "snow_mountain", "cn_line": "白雪压住山川的回声", "en_line": "Snow seals the echo of the range.", "style": "epic"},
    {"keyword": "雪山", "scene_tag": "snow_mountain", "cn_line": "风掠过冰脊，时间悄悄改写地貌", "en_line": "Wind skims the ice ridge and time redraws the land.", "style": "epic"},
    {"keyword": "雪山", "scene_tag": "snow_mountain", "cn_line": "人总要在寒冷里学会回身", "en_line": "We learn to turn back in the cold.", "style": "poetic"},
    {"keyword": "海岸", "scene_tag": "coast", "cn_line": "海浪先把名字抹掉", "en_line": "The tide erases names before the shore remembers them.", "style": "lyrical"},
    {"keyword": "海岸", "scene_tag": "coast", "cn_line": "风把潮汐磨成一条漫长的日记", "en_line": "Wind polishes the tides into a long, patient diary.", "style": "lyrical"},
    {"keyword": "海岸", "scene_tag": "coast", "cn_line": "回到岸边时，才明白人也会被浪打亮", "en_line": "Only by the shore do we understand how the sea reveals us.", "style": "reflective"},
    {"keyword": "沙漠", "scene_tag": "desert", "cn_line": "日光把地平线压成一枚旧印章", "en_line": "Sunlight stamps the horizon like a worn seal.", "style": "epic"},
    {"keyword": "沙漠", "scene_tag": "desert", "cn_line": "风携着时间沿着沙脊走动", "en_line": "Wind carries time along the dune ridges.", "style": "desolate"},
    {"keyword": "沙漠", "scene_tag": "desert", "cn_line": "所有归途都要先经过一场无声的消耗", "en_line": "Every return begins with a quiet, consuming distance.", "style": "reflective"},
    {"keyword": "古镇", "scene_tag": "old_town", "cn_line": "青石巷里，光阴低低地呼吸", "en_line": "In the alley of stone, time breathes with restraint.", "style": "nostalgic"},
    {"keyword": "古镇", "scene_tag": "old_town", "cn_line": "屋檐下的雨，慢慢把故事晒干", "en_line": "Rain under the eaves slowly dries the stories to dust.", "style": "nostalgic"},
    {"keyword": "古镇", "scene_tag": "old_town", "cn_line": "人终于懂得，归处往往是石板与灯影", "en_line": "We learn that home is often stone and lamplight.", "style": "reflective"},
    {"keyword": "草原", "scene_tag": "grassland", "cn_line": "风把地面吹成一条无尽的线", "en_line": "The wind draws the ground into an endless line.", "style": "expansive"},
    {"keyword": "草原", "scene_tag": "grassland", "cn_line": "晨雾在远处慢慢铺开，像一场未说完的故事", "en_line": "Morning mist opens far away like an unfinished story.", "style": "expansive"},
    {"keyword": "草原", "scene_tag": "grassland", "cn_line": "人只是被草原托起的一个微小影子", "en_line": "We are only a small shadow held by the grassland.", "style": "reflective"},
    {"keyword": "森林", "scene_tag": "forest", "cn_line": "树影把光线切成一页页沉默", "en_line": "Tree shadows divide the light into pages of silence.", "style": "mystic"},
    {"keyword": "森林", "scene_tag": "forest", "cn_line": "雾在林间缓慢迁徙，像一场无声的时光旅行", "en_line": "Mist drifts through the woods like a silent journey of time.", "style": "mystic"},
    {"keyword": "森林", "scene_tag": "forest", "cn_line": "终究，回到树根时，灵魂才有了落处", "en_line": "Only returning to the roots does the soul find a place to rest.", "style": "reflective"},
    {"keyword": "禾木", "scene_tag": "forest_mountain", "cn_line": "山谷里，雾气先学会沉默", "en_line": "In the valley, the mist learns silence before dawn.", "style": "poetic"},
    {"keyword": "禾木", "scene_tag": "forest_mountain", "cn_line": "林间的风沿着水声一路往前走", "en_line": "The wind through the woods carries the water's voice onward.", "style": "poetic"},
    {"keyword": "禾木", "scene_tag": "forest_mountain", "cn_line": "我们终会回到树影底下，看看自己是否仍有人心", "en_line": "We return to the shade of trees to ask whether the heart remains.", "style": "reflective"},
]


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            scene_tag TEXT NOT NULL,
            cn_line TEXT NOT NULL,
            en_line TEXT NOT NULL,
            style TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS images (
            image_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            image_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            subject_box TEXT NOT NULL,
            crop_window TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            keyword TEXT,
            chosen_copy_id INTEGER,
            result_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("SELECT COUNT(*) FROM templates")
    if conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO templates (keyword, scene_tag, cn_line, en_line, style) VALUES (?, ?, ?, ?, ?)",
            [
                (item["keyword"], item["scene_tag"], item["cn_line"], item["en_line"], item["style"])
                for item in TEMPLATE_SEEDS
            ],
        )
    conn.commit()
    conn.close()


def add_image_record(image_id: str, path: str, width: int, height: int, created_at: str | None = None) -> None:
    conn = get_connection()
    created_at = created_at or datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO images (image_id, path, width, height, created_at) VALUES (?, ?, ?, ?, ?)",
        (image_id, path, width, height, created_at),
    )
    conn.commit()
    conn.close()


def get_image_record(image_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM images WHERE image_id = ?", (image_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_analysis_result(image_id: str, role: str, subject_box: list[float], crop_window: dict[str, float | int], created_at: str | None = None) -> None:
    conn = get_connection()
    created_at = created_at or datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO analysis_results (image_id, role, subject_box, crop_window, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            image_id,
            role,
            json.dumps(subject_box),
            json.dumps(crop_window),
            created_at,
        ),
    )
    conn.commit()
    conn.close()


def get_analysis_result(image_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM analysis_results WHERE image_id = ?", (image_id,)).fetchone()
    conn.close()
    if not row:
        return None
    payload = dict(row)
    payload["subject_box"] = json.loads(payload["subject_box"])
    payload["crop_window"] = json.loads(payload["crop_window"])
    return payload


def get_templates_for_keyword(keyword: str) -> list[dict[str, Any]]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM templates WHERE keyword LIKE ? ORDER BY id ASC",
        (f"%{keyword}%",),
    ).fetchall()
    if rows:
        conn.close()
        return [dict(row) for row in rows]
    # Fuzzy fallback across keyword tokens and scene tags
    rows = conn.execute(
        "SELECT * FROM templates WHERE scene_tag LIKE ? OR keyword LIKE ? ORDER BY id ASC",
        (f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_template_by_id(template_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_template_count(keyword: str, limit: int = 3) -> list[dict[str, Any]]:
    matches = get_templates_for_keyword(keyword)
    if len(matches) >= limit:
        return matches[:limit]
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM templates WHERE keyword != ? ORDER BY id ASC LIMIT ?",
        (keyword, limit * 2),
    ).fetchall()
    conn.close()
    return [dict(row) for row in matches + [dict(r) for r in rows if dict(r) not in matches]][:limit]


def add_history_record(job_id: str, keyword: str | None, chosen_copy_id: int | None, result_path: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO history (id, keyword, chosen_copy_id, result_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (job_id, keyword, chosen_copy_id, result_path, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def cleanup_expired_uploads(ttl_hours: int = 24) -> int:
    if ttl_hours <= 0:
        ttl_hours = 24
    cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
    conn = get_connection()
    rows = conn.execute("SELECT image_id, path FROM images WHERE created_at < ?", (cutoff.isoformat(timespec="seconds"),)).fetchall()
    count = 0
    for row in rows:
        path = Path(row["path"])
        if path.exists():
            path.unlink(missing_ok=True)
        conn.execute("DELETE FROM analysis_results WHERE image_id = ?", (row["image_id"],))
        conn.execute("DELETE FROM images WHERE image_id = ?", (row["image_id"],))
        count += 1
    conn.commit()
    conn.close()
    return count


def list_recent_history(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def ensure_runtime_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


init_db()
ensure_runtime_dirs()
