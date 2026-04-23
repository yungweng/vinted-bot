from vinted_bot.config import SCRAPER


def search_catalog(session, params):
    url = f"{SCRAPER['base_url']}/api/v2/catalog/items"
    r = session.get(url, params=params)
    data = r.json()
    return data.get("items", []) or []


def get_item_detail(session, item_id):
    url = f"{SCRAPER['base_url']}/api/v2/items/{item_id}"
    r = session.get(url)
    data = r.json()
    return data.get("item", {}) or {}
