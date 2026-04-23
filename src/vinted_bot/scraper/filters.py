from urllib.parse import urlparse, parse_qs


# Vinted's Web-UI benutzt PHP-Array-Keys wie catalog[]=5. Die API mag
# catalog_ids=5,10. Hier das Mapping.
_UI_TO_API = {
    "catalog": "catalog_ids",
    "brand": "brand_ids",
    "size": "size_ids",
    "status": "status_ids",
    "color": "color_ids",
    "material": "material_ids",
    "video_game_rating": "video_game_rating_ids",
}


def params_from_url(url):
    parsed = urlparse(url)
    raw = parse_qs(parsed.query, keep_blank_values=False)
    out = {}
    for key, values in raw.items():
        normalized = key[:-2] if key.endswith("[]") else key
        api_key = _UI_TO_API.get(normalized, normalized)
        out[api_key] = ",".join(values) if len(values) > 1 else values[0]
    return out


def build_search_params(search_url, overrides):
    params = params_from_url(search_url) if search_url else {}
    for key, value in overrides.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            params[key] = ",".join(str(x) for x in value)
        else:
            params[key] = value
    return params
