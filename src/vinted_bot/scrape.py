import time
import traceback
from pathlib import Path

from vinted_bot.config import PATHS, PROVIDERS, SCRAPER, SEARCH_OVERRIDES
from vinted_bot.pipeline.classify import build_system_prompt, classify
from vinted_bot.pipeline.images import download_item_images
from vinted_bot.pipeline.ocr import ocr_images
from vinted_bot.pipeline.prompt_builder import build_user_message
from vinted_bot.scraper.filters import build_search_params
from vinted_bot.scraper.html_scrape import extract_description, extract_shipping, fetch_item_page
from vinted_bot.scraper.normalize import normalize_item
from vinted_bot.scraper.session import VintedSession
from vinted_bot.scraper.vinted_api import search_catalog
from vinted_bot.storage.db import (
    connect,
    get_all_config,
    get_search,
    item_exists,
    save_item,
    update_search_status,
)


def run_search(search_id, log=print):
    """Run scrape + classify pipeline for a single search row. Updates its status."""
    try:
        _run(search_id, log)
    except Exception as e:
        log(f"FEHLER: {e}")
        traceback.print_exc()
        with connect() as con:
            update_search_status(con, search_id, "error", error=str(e))


def _run(search_id, log):
    with connect() as con:
        search = get_search(con, search_id)
        if not search:
            raise RuntimeError(f"Suche {search_id} nicht gefunden.")
        config = get_all_config(con)
        update_search_status(con, search_id, "running")

    provider_key = (config.get("provider") or "openrouter").strip()
    if provider_key not in PROVIDERS:
        raise RuntimeError(f"Unbekannter Provider in Einstellungen: {provider_key!r}")
    provider = PROVIDERS[provider_key]

    api_key = (config.get(f"{provider_key}_api_key") or "").strip()
    if not api_key:
        raise RuntimeError(
            f"Kein API-Key fuer {provider['label']} in den Einstellungen."
        )

    default_model = (config.get(f"{provider_key}_model") or provider["default_model"]).strip()
    model = (search.get("model") or default_model).strip()
    base_url = provider["base_url"]
    max_entries = search.get("max_entries")
    if not max_entries or int(max_entries) <= 0:
        max_entries = int(config.get("max_entries") or 50)
    else:
        max_entries = int(max_entries)

    system_prompt = build_system_prompt(
        search.get("ja_prompt") or config.get("default_ja_prompt", ""),
        search.get("nein_prompt") or config.get("default_nein_prompt", ""),
        search.get("vielleicht_prompt") or config.get("default_vielleicht_prompt", ""),
        search.get("sonderregeln") or config.get("default_sonderregeln", ""),
    )

    Path(PATHS["images"]).mkdir(parents=True, exist_ok=True)

    params = build_search_params(search["url"], SEARCH_OVERRIDES)
    log(f"Suche {search_id}: Katalog abrufen...")
    session = VintedSession()
    stubs = search_catalog(session, params)
    log(f"  {len(stubs)} Treffer auf Seite {params.get('page', 1)}.")

    stubs = stubs[:max_entries]
    log(f"  verarbeite {len(stubs)} (max_entries={max_entries}).")

    processed = 0
    skipped = 0
    errors = 0

    for i, stub in enumerate(stubs, start=1):
        vinted_id = stub.get("id")
        if not vinted_id:
            continue

        title_preview = (stub.get("title") or "")[:60]
        log(f"[{i}/{len(stubs)}] {vinted_id} - {title_preview}")

        with connect() as con:
            if item_exists(con, search_id, vinted_id):
                log("  bereits klassifiziert, skip.")
                skipped += 1
                continue

        try:
            html = fetch_item_page(session, stub.get("url"))
            stub["description"] = extract_description(html)
            stub["_shipping_from_html"] = extract_shipping(html)
        except Exception as e:
            log(f"  html-fetch fehlgeschlagen: {e}")
            errors += 1
            time.sleep(SCRAPER["request_delay_seconds"])
            continue

        item = normalize_item(stub)
        if not item.get("id"):
            log("  kein item-id, skip.")
            errors += 1
            continue

        image_paths = download_item_images(item["id"], item["photo_urls"])
        log(f"  {len(image_paths)} Bilder, OCR laeuft...")
        ocr_text = ocr_images(image_paths)

        user_msg = build_user_message(item, ocr_text)
        try:
            verdict, reason, raw = classify(
                user_msg,
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                base_url=base_url,
            )
        except Exception as e:
            log(f"  classify fehlgeschlagen: {e}")
            errors += 1
            continue

        if verdict == "ja":
            log("  -> ja")
        elif verdict == "vielleicht":
            log(f"  -> vielleicht: {reason or '(kein Grund)'}")
        else:
            log(f"  -> nein: {reason or '(kein Grund)'}")

        with connect() as con:
            save_item(
                con, search_id, item, image_paths, ocr_text,
                verdict, reason, raw, model,
            )
        processed += 1
        time.sleep(SCRAPER["request_delay_seconds"])

    log(f"Fertig: {processed} neu, {skipped} skip, {errors} errors.")
    with connect() as con:
        update_search_status(con, search_id, "done")
