import os
import sys
import time
from pathlib import Path

from vinted_bot.config import (
    CLASSIFIER,
    MAX_ITEMS_PER_RUN,
    PATHS,
    SCRAPER,
    SEARCH_OVERRIDES,
    SEARCH_URL,
)
from vinted_bot.pipeline.classify import classify
from vinted_bot.pipeline.images import download_item_images
from vinted_bot.pipeline.ocr import ocr_images
from vinted_bot.pipeline.prompt_builder import build_user_message
from vinted_bot.scraper.filters import build_search_params
from vinted_bot.scraper.html_scrape import extract_description, extract_shipping, fetch_item_page
from vinted_bot.scraper.normalize import normalize_item
from vinted_bot.scraper.session import VintedSession
from vinted_bot.scraper.vinted_api import search_catalog
from vinted_bot.storage.db import connect, item_exists, save_item


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY env var ist nicht gesetzt.")
        print("       export OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    Path(PATHS["images"]).mkdir(parents=True, exist_ok=True)

    params = build_search_params(SEARCH_URL, SEARCH_OVERRIDES)
    print("Search-Parameter:")
    for key, value in params.items():
        print(f"  {key}: {value}")

    print("\nVinted-Session aufbauen...")
    session = VintedSession()

    print("Katalog abrufen...")
    stubs = search_catalog(session, params)
    print(f"  {len(stubs)} Artikel auf Seite {params.get('page', 1)} gefunden.")

    if MAX_ITEMS_PER_RUN is not None:
        stubs = stubs[:MAX_ITEMS_PER_RUN]
        print(f"  auf {len(stubs)} Artikel begrenzt (MAX_ITEMS_PER_RUN).")

    processed = 0
    skipped = 0
    errors = 0

    with connect() as con:
        for i, stub in enumerate(stubs, start=1):
            item_id = stub.get("id")
            if not item_id:
                continue

            title_preview = (stub.get("title") or "")[:60]
            print(f"\n[{i}/{len(stubs)}] {item_id} - {title_preview}")

            if item_exists(con, item_id):
                print("  bereits klassifiziert, skip.")
                skipped += 1
                continue

            # Katalog: Preis, Kaeuferschutz (service_fee), Groesse, Bilder.
            # HTML: echte Beschreibung + tatsaechlicher Versandpreis (ungleich service_fee).
            item_url = stub.get("url")
            try:
                html = fetch_item_page(session, item_url)
                stub["description"] = extract_description(html)
                stub["_shipping_from_html"] = extract_shipping(html)
            except Exception as e:
                print(f"  html-fetch fehlgeschlagen: {e}")
                errors += 1
                time.sleep(SCRAPER["request_delay_seconds"])
                continue

            item = normalize_item(stub)
            if not item.get("id"):
                print("  kein item-id, skip.")
                errors += 1
                continue

            ship = item.get("shipping")
            bp = item.get("buyer_protection")
            print(
                f"  Preis {item.get('price')} EUR | "
                f"Kaeuferschutz {bp if bp is not None else '?'} | "
                f"Versand {ship if ship is not None else '?'}"
            )

            image_paths = download_item_images(item["id"], item["photo_urls"])
            print(f"  {len(image_paths)} Bilder geladen, OCR laeuft...")
            ocr_text = ocr_images(image_paths)
            preview = ocr_text.replace("\n", " / ")[:80]
            print(f"  OCR: {preview}")

            user_msg = build_user_message(item, ocr_text)
            try:
                verdict, reason, raw = classify(user_msg)
            except Exception as e:
                print(f"  classify fehlgeschlagen: {e}")
                errors += 1
                continue
            if verdict == "ja":
                print(f"  -> ja")
            elif verdict == "vielleicht":
                print(f"  -> vielleicht: {reason or '(kein Grund)'}")
            else:
                print(f"  -> nein: {reason or '(kein Grund)'}")

            save_item(
                con, item, image_paths, ocr_text,
                verdict, reason, raw, CLASSIFIER["model"],
            )
            processed += 1
            con.commit()
            time.sleep(SCRAPER["request_delay_seconds"])

    print("\n=== Fertig ===")
    print(f"  neu klassifiziert: {processed}")
    print(f"  skipped (schon in db): {skipped}")
    print(f"  errors: {errors}")
    print("\nStart the dashboard: vinted-bot")


if __name__ == "__main__":
    main()
