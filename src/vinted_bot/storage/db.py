import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from vinted_bot.config import PATHS


_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_initialized = False


DEFAULT_CONFIG = {
    "api_key": "",
    "model": "anthropic/claude-haiku-4.5",
    "max_entries": "50",
    "default_ja_prompt": "",
    "default_nein_prompt": "",
    "default_vielleicht_prompt": "",
    "default_sonderregeln": "",
}


def _read_prompt(name):
    path = _PROMPTS_DIR / f"default_{name}.txt"
    if path.exists():
        return path.read_text().strip()
    return ""


def _seed_defaults(con):
    existing = {row[0] for row in con.execute("SELECT key FROM app_config")}
    seed = dict(DEFAULT_CONFIG)
    seed["default_ja_prompt"] = _read_prompt("ja")
    seed["default_nein_prompt"] = _read_prompt("nein")
    seed["default_vielleicht_prompt"] = _read_prompt("vielleicht")
    seed["default_sonderregeln"] = _read_prompt("sonderregeln")
    for key, value in seed.items():
        if key not in existing:
            con.execute(
                "INSERT INTO app_config (key, value) VALUES (?, ?)",
                (key, value),
            )


def _init():
    global _initialized
    if _initialized:
        return
    Path(PATHS["db"]).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(PATHS["db"])
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(_SCHEMA_PATH.read_text())
    _seed_defaults(con)
    con.commit()
    con.close()
    _initialized = True


@contextmanager
def connect():
    _init()
    con = sqlite3.connect(PATHS["db"])
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


# -------- config --------

def get_config(con, key, default=None):
    row = con.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return row["value"]


def get_all_config(con):
    rows = con.execute("SELECT key, value FROM app_config").fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_config(con, key, value):
    con.execute(
        """
        INSERT INTO app_config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value if value is not None else ""),
    )


# -------- searches --------

def create_search(con, *, name, url, ja_prompt, nein_prompt, vielleicht_prompt,
                  sonderregeln, max_entries, model):
    cur = con.execute(
        """
        INSERT INTO searches
          (name, url, ja_prompt, nein_prompt, vielleicht_prompt, sonderregeln,
           max_entries, model, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (name, url, ja_prompt, nein_prompt, vielleicht_prompt, sonderregeln,
         max_entries, model),
    )
    return cur.lastrowid


def get_search(con, search_id):
    row = con.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    return dict(row) if row else None


def list_searches(con):
    rows = con.execute(
        """
        SELECT
          s.*,
          (SELECT COUNT(*) FROM items WHERE search_id = s.id) AS total,
          (SELECT COUNT(*) FROM items i JOIN classifications c ON c.item_id = i.id
           WHERE i.search_id = s.id AND c.verdict = 'ja') AS count_ja,
          (SELECT COUNT(*) FROM items i JOIN classifications c ON c.item_id = i.id
           WHERE i.search_id = s.id AND c.verdict = 'vielleicht') AS count_vielleicht,
          (SELECT COUNT(*) FROM items i JOIN classifications c ON c.item_id = i.id
           WHERE i.search_id = s.id AND c.verdict = 'nein') AS count_nein,
          (SELECT COUNT(*) FROM items i JOIN user_actions u ON u.item_id = i.id
           WHERE i.search_id = s.id) AS count_decided
        FROM searches s
        ORDER BY s.created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def update_search_status(con, search_id, status, error=None):
    if status in ("done", "error"):
        con.execute(
            "UPDATE searches SET status = ?, error = ?, finished_at = datetime('now') WHERE id = ?",
            (status, error, search_id),
        )
    else:
        con.execute(
            "UPDATE searches SET status = ?, error = ? WHERE id = ?",
            (status, error, search_id),
        )


def delete_search(con, search_id):
    con.execute("DELETE FROM searches WHERE id = ?", (search_id,))


# -------- items --------

def item_exists(con, search_id, vinted_id):
    row = con.execute(
        "SELECT 1 FROM items WHERE search_id = ? AND vinted_id = ?",
        (search_id, vinted_id),
    ).fetchone()
    return row is not None


def save_item(con, search_id, item, image_rel_paths, ocr_text,
              verdict, reason, raw_response, model):
    cur = con.execute(
        """
        INSERT INTO items (
          vinted_id, search_id, title, brand, size, condition, color,
          price, buyer_protection, shipping, currency, uploaded_at, url,
          description, ocr_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["id"],
            search_id,
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
    row_id = cur.lastrowid
    for idx, rel in enumerate(image_rel_paths):
        con.execute(
            "INSERT INTO images (item_id, idx, local_path) VALUES (?, ?, ?)",
            (row_id, idx, rel),
        )
    con.execute(
        """
        INSERT INTO classifications
          (item_id, verdict, reason, model, classified_at, raw_response)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
        """,
        (row_id, verdict, reason, model, raw_response),
    )
    return row_id


# -------- reset --------

def reset_db():
    global _initialized
    db_path = Path(PATHS["db"])
    if db_path.exists():
        db_path.unlink()
    images_dir = Path(PATHS["images"])
    if images_dir.exists():
        shutil.rmtree(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)
    _initialized = False
    _init()
