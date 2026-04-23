import sqlite3
from contextlib import contextmanager
from pathlib import Path

from vinted_bot.config import PATHS


_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_initialized = False


def _init():
    global _initialized
    if _initialized:
        return
    Path(PATHS["db"]).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(PATHS["db"])
    con.executescript(_SCHEMA_PATH.read_text())
    con.commit()
    con.close()
    _initialized = True


@contextmanager
def connect():
    _init()
    con = sqlite3.connect(PATHS["db"])
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def item_exists(con, item_id):
    row = con.execute(
        "SELECT 1 FROM classifications WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    return row is not None


def save_item(con, item, image_rel_paths, ocr_text, verdict, reason, raw_response, model):
    con.execute(
        """
        INSERT OR REPLACE INTO items (
          id, title, brand, size, condition, color,
          price, buyer_protection, shipping, currency, uploaded_at, url,
          description, ocr_text, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            item["id"],
            item.get("title"),
            item.get("brand"),
            item.get("size"),
            item.get("condition"),
            item.get("color"),
            item.get("price"),
            item.get("buyer_protection"),
            item.get("shipping"),
            item.get("currency"),
            str(item.get("uploaded_at") or ""),
            item.get("url"),
            item.get("description"),
            ocr_text,
        ),
    )
    con.execute("DELETE FROM images WHERE item_id = ?", (item["id"],))
    for idx, rel in enumerate(image_rel_paths):
        con.execute(
            "INSERT INTO images (item_id, idx, local_path) VALUES (?, ?, ?)",
            (item["id"], idx, rel),
        )
    con.execute(
        """
        INSERT OR REPLACE INTO classifications
          (item_id, verdict, reason, model, classified_at, raw_response)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
        """,
        (item["id"], verdict, reason, model, raw_response),
    )
