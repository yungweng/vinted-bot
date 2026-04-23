from pathlib import Path

from curl_cffi import requests as curl_requests

from vinted_bot.config import PATHS, SCRAPER


_ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}


def _guess_ext(url):
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    return ext if ext in _ALLOWED_EXT else "jpg"


def download_item_images(item_id, photo_urls):
    base = Path(PATHS["images"]) / str(item_id)
    base.mkdir(parents=True, exist_ok=True)
    rel_paths = []
    for idx, url in enumerate(photo_urls):
        if not url:
            continue
        ext = _guess_ext(url)
        rel = f"{item_id}/{idx:02d}.{ext}"
        full = base / f"{idx:02d}.{ext}"
        if full.exists() and full.stat().st_size > 0:
            rel_paths.append(rel)
            continue
        try:
            r = curl_requests.get(
                url,
                impersonate=SCRAPER["impersonate"],
                timeout=SCRAPER["request_timeout"],
            )
            r.raise_for_status()
            full.write_bytes(r.content)
            rel_paths.append(rel)
        except Exception as e:
            print(f"  image {idx} failed: {e}")
    return rel_paths
