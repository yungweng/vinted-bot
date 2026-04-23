import json

from vinted_bot.config import SCRAPER, SEARCH_OVERRIDES, SEARCH_URL
from vinted_bot.scraper.filters import build_search_params
from vinted_bot.scraper.html_scrape import extract_description, extract_shipping, shipping_debug
from vinted_bot.scraper.normalize import normalize_item
from vinted_bot.scraper.session import VintedSession
from vinted_bot.scraper.vinted_api import search_catalog


def main():
    session = VintedSession()
    params = build_search_params(SEARCH_URL, SEARCH_OVERRIDES)
    stubs = search_catalog(session, params)
    print(f"Katalog: {len(stubs)} Items.\n")

    if not stubs:
        return

    first = stubs[0]
    print("=== KATALOG-ROHDATEN ERSTES ITEM ===")
    print(f"Keys: {sorted(first.keys())}\n")
    print(json.dumps(first, indent=2, ensure_ascii=False, default=str)[:3000])
    print("\n" + "=" * 60 + "\n")

    item_id = first.get("id")
    print(f"=== DETAIL-ENDPOINTS PROBIEREN FUER ITEM {item_id} ===\n")

    candidates = [
        f"{SCRAPER['base_url']}/api/v2/items/{item_id}",
        f"{SCRAPER['base_url']}/api/v2/items/{item_id}/details",
        f"{SCRAPER['base_url']}/api/v2/item_info/{item_id}",
    ]

    for url in candidates:
        print(f"GET {url}")
        try:
            r = session.session.get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": SCRAPER["base_url"] + "/",
                    **({"X-CSRF-Token": session.csrf_token} if session.csrf_token else {}),
                },
                timeout=SCRAPER["request_timeout"],
            )
            print(f"  status: {r.status_code}")
            print(f"  body preview: {r.text[:300]}")
        except Exception as e:
            print(f"  exception: {e}")
        print()

    web_url = first.get("url") or f"{SCRAPER['base_url']}/items/{item_id}"
    print(f"=== HTML-SEITE + BESCHREIBUNG ===\nGET {web_url}")
    r = session.session.get(
        web_url,
        timeout=SCRAPER["request_timeout"],
        headers={"Referer": SCRAPER["base_url"] + "/"},
    )
    print(f"  status: {r.status_code}, length: {len(r.text)}")
    description = extract_description(r.text)
    print(f"  description length: {len(description)}")
    print(f"  description preview:")
    print(f"    {description[:600]!r}")
    print()

    shipping = extract_shipping(r.text)
    print(f"  shipping aus HTML (final): {shipping!r}")
    print()

    print("  -- Shipping-Diagnose --")
    ship_info = shipping_debug(r.text)
    print(f"  text_matches ({len(ship_info['text_matches'])}):")
    for pattern, full, value in ship_info["text_matches"]:
        print(f"    match='{full}' -> {value}")
    print(f"  json_matches ({len(ship_info['json_matches'])}):")
    for pattern, raw, value in ship_info["json_matches"][:10]:
        print(f"    raw='{raw}' -> {value}")
    print(f"  'Versand'-Kontext im Text ({len(ship_info['versand_context'])} Stellen):")
    for i, snippet in enumerate(ship_info["versand_context"][:10], 1):
        print(f"    [{i}] {snippet}")
    print()

    print("=== NORMALISIERT (Katalog + HTML) ===")
    first["description"] = description
    first["_shipping_from_html"] = shipping
    normalized = normalize_item(first)
    for key in ("id", "title", "brand", "size", "condition", "color",
               "price", "buyer_protection", "shipping", "currency", "url"):
        print(f"  {key}: {normalized.get(key)!r}")
    print(f"  photo_urls: {len(normalized.get('photo_urls') or [])} urls")
    desc = normalized.get("description") or ""
    print(f"  description ({len(desc)} chars): {desc[:200]!r}")


if __name__ == "__main__":
    main()
