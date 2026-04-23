def _coerce_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _price(raw_price):
    if isinstance(raw_price, dict):
        return _coerce_float(raw_price.get("amount")), raw_price.get("currency_code") or "EUR"
    return _coerce_float(raw_price), "EUR"


def _brand(raw):
    if raw.get("brand_title"):
        return raw["brand_title"]
    brand = raw.get("brand")
    if isinstance(brand, dict):
        return brand.get("title", "")
    if isinstance(brand, str):
        return brand
    return ""


def _color(raw):
    for key in ("color1", "color2"):
        value = raw.get(key)
        if isinstance(value, dict) and value.get("title"):
            return value["title"]
    colors = raw.get("colors")
    if isinstance(colors, list) and colors:
        first = colors[0]
        if isinstance(first, dict) and first.get("title"):
            return first["title"]
        if isinstance(first, str):
            return first
    return ""


def _photo_urls(raw):
    photos = raw.get("photos") or []
    urls = []
    for p in photos:
        if isinstance(p, dict):
            url = p.get("full_size_url") or p.get("url")
            if url:
                urls.append(url)
    if not urls:
        single = raw.get("photo")
        if isinstance(single, dict):
            url = single.get("full_size_url") or single.get("url")
            if url:
                urls.append(url)
    return urls


def normalize_item(raw):
    price, currency = _price(raw.get("price") or raw.get("total_item_price"))
    buyer_protection, _ = _price(raw.get("service_fee"))
    # Echter Versandpreis kommt aus dem HTML-Scrape, wird vom Pipeline-Code in
    # den stub als "_shipping_from_html" injiziert. Fallback auf shipping_price.
    shipping = raw.get("_shipping_from_html")
    if shipping is None:
        shipping, _ = _price(raw.get("shipping_price"))
    return {
        "id": raw.get("id"),
        "title": raw.get("title") or "",
        "brand": _brand(raw),
        "size": raw.get("size_title") or "",
        "condition": raw.get("status") or raw.get("condition") or "",
        "color": _color(raw),
        "price": price,
        "buyer_protection": buyer_protection,
        "shipping": shipping,
        "currency": currency,
        "uploaded_at": raw.get("created_at_ts") or "",
        "url": raw.get("url") or "",
        "description": (raw.get("description") or "").strip(),
        "photo_urls": _photo_urls(raw),
    }
