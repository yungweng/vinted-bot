from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import PATHS
from storage.db import connect


BASE = Path(__file__).parent
app = FastAPI()
templates = Jinja2Templates(directory=str(BASE / "templates"))

Path(PATHS["images"]).mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=PATHS["images"]), name="images")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, show: str = "ja"):
    base_query = """
        SELECT
          i.id, i.title, i.brand, i.size, i.condition, i.color,
          i.price, i.buyer_protection, i.shipping, i.currency, i.url,
          c.verdict, c.reason, u.action,
          (SELECT local_path FROM images WHERE item_id = i.id ORDER BY idx LIMIT 1) AS thumb
        FROM items i
        JOIN classifications c ON c.item_id = i.id
        LEFT JOIN user_actions u ON u.item_id = i.id
    """
    with connect() as con:
        counts = dict(
            con.execute(
                "SELECT verdict, COUNT(*) FROM classifications GROUP BY verdict"
            ).fetchall()
        )
        if show == "all":
            rows = con.execute(base_query + " ORDER BY i.fetched_at DESC").fetchall()
        elif show == "nein":
            rows = con.execute(
                base_query + " WHERE c.verdict = 'nein' ORDER BY i.fetched_at DESC"
            ).fetchall()
        elif show == "vielleicht":
            rows = con.execute(
                base_query
                + " WHERE c.verdict = 'vielleicht' AND u.action IS NULL"
                + " ORDER BY i.fetched_at DESC"
            ).fetchall()
        elif show == "decided":
            rows = con.execute(
                base_query + " WHERE u.action IS NOT NULL ORDER BY u.decided_at DESC"
            ).fetchall()
        else:
            show = "ja"
            rows = con.execute(
                base_query
                + " WHERE c.verdict = 'ja' AND u.action IS NULL"
                + " ORDER BY i.fetched_at DESC"
            ).fetchall()
    items = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "items": items, "show": show, "counts": counts},
    )


@app.get("/item/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int):
    with connect() as con:
        row = con.execute(
            """
            SELECT i.*, c.verdict, c.reason, c.raw_response, u.action
            FROM items i
            JOIN classifications c ON c.item_id = i.id
            LEFT JOIN user_actions u ON u.item_id = i.id
            WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        images = con.execute(
            "SELECT idx, local_path FROM images WHERE item_id = ? ORDER BY idx",
            (item_id,),
        ).fetchall()
    return templates.TemplateResponse(
        "item.html",
        {
            "request": request,
            "item": dict(row) if row else None,
            "images": [dict(i) for i in images],
        },
    )


@app.post("/item/{item_id}/action")
def set_action(item_id: int, action: str = Form(...)):
    if action not in {"kaufen", "verhandeln", "nein"}:
        return JSONResponse({"ok": False, "error": "invalid action"}, status_code=400)
    with connect() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO user_actions (item_id, action, decided_at)
            VALUES (?, ?, datetime('now'))
            """,
            (item_id, action),
        )
    return {"ok": True, "action": action}
