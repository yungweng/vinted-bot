from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vinted_bot.config import PATHS, PROVIDERS
from vinted_bot.scrape import run_search
from vinted_bot.storage.db import (
    connect,
    create_search,
    get_all_config,
    get_search,
    list_searches,
    reset_db,
    set_config,
)


BASE = Path(__file__).parent
app = FastAPI()
templates = Jinja2Templates(directory=str(BASE / "templates"))

Path(PATHS["images"]).mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=PATHS["images"]), name="images")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# ---------- new search ----------

@app.get("/", response_class=HTMLResponse)
def new_search_form(request: Request):
    with connect() as con:
        config = get_all_config(con)
    provider_key = config.get("provider") or "openrouter"
    provider = PROVIDERS.get(provider_key, PROVIDERS["openrouter"])
    default_model = config.get(f"{provider_key}_model") or provider["default_model"]
    has_provider_key = bool((config.get(f"{provider_key}_api_key") or "").strip())
    defaults = {
        "max_entries": int(config.get("max_entries") or 50),
        "model": default_model,
        "ja_prompt": config.get("default_ja_prompt") or "",
        "nein_prompt": config.get("default_nein_prompt") or "",
        "vielleicht_prompt": config.get("default_vielleicht_prompt") or "",
        "sonderregeln": config.get("default_sonderregeln") or "",
    }
    return templates.TemplateResponse(
        request,
        "new_search.html",
        {
            "active": "new",
            "defaults": defaults,
            "has_provider_key": has_provider_key,
            "provider_label": provider["label"],
        },
    )


@app.post("/searches")
def create_search_route(
    background_tasks: BackgroundTasks,
    name: str = Form(""),
    url: str = Form(...),
    max_entries: int = Form(50),
    model: str = Form(""),
    ja_prompt: str = Form(""),
    nein_prompt: str = Form(""),
    vielleicht_prompt: str = Form(""),
    sonderregeln: str = Form(""),
):
    with connect() as con:
        search_id = create_search(
            con,
            name=name.strip() or None,
            url=url.strip(),
            ja_prompt=ja_prompt.strip(),
            nein_prompt=nein_prompt.strip(),
            vielleicht_prompt=vielleicht_prompt.strip(),
            sonderregeln=sonderregeln.strip(),
            max_entries=max_entries,
            model=model.strip() or None,
        )
    background_tasks.add_task(run_search, search_id)
    return RedirectResponse(f"/searches/{search_id}", status_code=303)


# ---------- list searches ----------

@app.get("/searches", response_class=HTMLResponse)
def searches_list(request: Request):
    with connect() as con:
        rows = list_searches(con)
    return templates.TemplateResponse(
        request,
        "searches.html",
        {"active": "searches", "searches": rows},
    )


# ---------- search detail ----------

_BASE_ITEM_QUERY = """
    SELECT
      i.id, i.title, i.brand, i.size, i.condition, i.color,
      i.price, i.buyer_protection, i.shipping, i.currency, i.url,
      c.verdict, c.reason, u.action,
      (SELECT local_path FROM images WHERE item_id = i.id ORDER BY idx LIMIT 1) AS thumb
    FROM items i
    JOIN classifications c ON c.item_id = i.id
    LEFT JOIN user_actions u ON u.item_id = i.id
    WHERE i.search_id = ?
"""


def _load_search_view(search_id: int, show: str):
    with connect() as con:
        search = get_search(con, search_id)
        if not search:
            return None
        counts_rows = con.execute(
            """
            SELECT c.verdict, COUNT(*) AS n
            FROM items i JOIN classifications c ON c.item_id = i.id
            WHERE i.search_id = ?
            GROUP BY c.verdict
            """,
            (search_id,),
        ).fetchall()
        counts = {r["verdict"]: r["n"] for r in counts_rows}
        counts["total"] = sum(counts.values())
        counts["decided"] = con.execute(
            """
            SELECT COUNT(*) FROM items i
            JOIN user_actions u ON u.item_id = i.id
            WHERE i.search_id = ?
            """,
            (search_id,),
        ).fetchone()[0]

        if show == "all":
            rows = con.execute(
                _BASE_ITEM_QUERY + " ORDER BY i.fetched_at DESC",
                (search_id,),
            ).fetchall()
        elif show == "nein":
            rows = con.execute(
                _BASE_ITEM_QUERY
                + " AND c.verdict = 'nein' ORDER BY i.fetched_at DESC",
                (search_id,),
            ).fetchall()
        elif show == "vielleicht":
            rows = con.execute(
                _BASE_ITEM_QUERY
                + " AND c.verdict = 'vielleicht' AND u.action IS NULL"
                + " ORDER BY i.fetched_at DESC",
                (search_id,),
            ).fetchall()
        elif show == "decided":
            rows = con.execute(
                _BASE_ITEM_QUERY
                + " AND u.action IS NOT NULL ORDER BY u.decided_at DESC",
                (search_id,),
            ).fetchall()
        else:
            show = "ja"
            rows = con.execute(
                _BASE_ITEM_QUERY
                + " AND c.verdict = 'ja' AND u.action IS NULL"
                + " ORDER BY i.fetched_at DESC",
                (search_id,),
            ).fetchall()
    return {
        "search": search,
        "items": [dict(r) for r in rows],
        "show": show,
        "counts": counts,
    }


@app.get("/searches/{search_id}", response_class=HTMLResponse)
def search_detail(request: Request, search_id: int, show: str = "ja"):
    view = _load_search_view(search_id, show)
    if view is None:
        return HTMLResponse("Suche nicht gefunden", status_code=404)
    return templates.TemplateResponse(
        request,
        "search_detail.html",
        {"active": "searches", **view},
    )


@app.get("/searches/{search_id}/content", response_class=HTMLResponse)
def search_content(request: Request, search_id: int, show: str = "ja"):
    view = _load_search_view(search_id, show)
    if view is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_search_content.html", view)


@app.get("/searches/{search_id}/status", response_class=HTMLResponse)
def search_status(request: Request, search_id: int):
    with connect() as con:
        search = get_search(con, search_id)
    if not search:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_status_pill.html", {"search": search})


# ---------- item detail ----------

@app.get("/item/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int, from_: str | None = None):
    from_search = from_ or request.query_params.get("from")
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
        request,
        "item.html",
        {
            "active": "searches",
            "item": dict(row) if row else None,
            "images": [dict(i) for i in images],
            "from_search": from_search or (row["search_id"] if row else None),
        },
    )


@app.post("/item/{item_id}/action")
def set_action(item_id: int, action: str = Form(...)):
    if action not in {"kaufen", "verhandeln", "nein"}:
        return JSONResponse({"ok": False, "error": "invalid action"}, status_code=400)
    with connect() as con:
        con.execute(
            """
            INSERT INTO user_actions (item_id, action, decided_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(item_id) DO UPDATE SET action = excluded.action, decided_at = excluded.decided_at
            """,
            (item_id, action),
        )
    return {"ok": True, "action": action}


# ---------- settings ----------

_SETTINGS_KEYS = (
    "provider",
    "max_entries",
    "default_ja_prompt",
    "default_nein_prompt",
    "default_vielleicht_prompt",
    "default_sonderregeln",
    *[f"{key}_api_key" for key in PROVIDERS],
    *[f"{key}_model" for key in PROVIDERS],
)


@app.get("/settings", response_class=HTMLResponse)
def settings_form(request: Request, saved: int = 0):
    with connect() as con:
        config = get_all_config(con)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active": "settings",
            "config": config,
            "providers": PROVIDERS,
            "saved": bool(saved),
        },
    )


@app.post("/settings")
async def save_settings(request: Request):
    form = await request.form()
    with connect() as con:
        for key in _SETTINGS_KEYS:
            if key in form:
                set_config(con, key, form.get(key, ""))
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/reset-db")
def reset_db_route():
    with connect() as con:
        config = get_all_config(con)
    reset_db()
    with connect() as con:
        for key, value in config.items():
            set_config(con, key, value)
    return RedirectResponse("/settings", status_code=303)
