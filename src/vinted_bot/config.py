from pathlib import Path

from platformdirs import user_data_dir

ROOT = Path(__file__).parent
DATA_DIR = Path(user_data_dir("vinted-bot", appauthor=False))
DATA_DIR.mkdir(parents=True, exist_ok=True)

OCR = {
    "languages": ["de", "en", "it"],
    "min_chars_for_valid": 10,
    "max_image_dim": 1600,
    "no_text_message": "Keine lesbaren Texte auf den Bildern erkannt.",
}

SCRAPER = {
    "request_delay_seconds": 1.5,
    "request_timeout": 20,
    "impersonate": "chrome136",
    "impersonate_fallbacks": ["chrome131", "chrome146", "chrome124"],
    "accept_language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "base_url": "https://www.vinted.de",
}

CLASSIFIER = {
    "max_tokens": 120,
    "temperature": 0.0,
    "base_url": "https://openrouter.ai/api/v1",
    "app_name": "vinted-bot",
    "app_url": "http://localhost",
}

SEARCH_OVERRIDES = {
    "per_page": 96,
    "page": 1,
}

PATHS = {
    "db": str(DATA_DIR / "vinted.sqlite"),
    "images": str(DATA_DIR / "images"),
}
