from pathlib import Path

ROOT = Path(__file__).parent

# Baseline-URL: alle Filter die du in der Vinted-Weboberflaeche klickst, landen hier.
# Die Query-Params werden automatisch in API-Parameter uebersetzt.
SEARCH_URL = "https://www.vinted.de/catalog?search_text=levis%20jeans%20herren&size_ids[]=208&size_ids[]=209&size_ids[]=210&size_ids[]=1638&size_ids[]=1639&size_ids[]=1640&size_ids[]=1641&size_ids[]=1642&size_ids[]=1662&size_ids[]=1643&page=1&time=1776978013&status_ids[]=1&status_ids[]=6&status_ids[]=2&status_ids[]=3&price_to=15&currency=EUR"

# Manuelle Overrides, ueberschreiben alles aus der URL. Leere Werte werden ignoriert.
SEARCH_OVERRIDES = {
    "price_to": 10,
    "currency": "EUR",
    "per_page": 96,
    "page": 1,
}

# Zum Testen auf kleine Runs begrenzen. None = alle Items der Seite.
MAX_ITEMS_PER_RUN = 50

CLASSIFIER = {
    # OpenRouter-Modellname. Alternativen siehe https://openrouter.ai/models
    # z.B. "anthropic/claude-haiku-4.5", "anthropic/claude-sonnet-4.5", "openai/gpt-4o-mini"
    "model": "anthropic/claude-haiku-4.5",
    "max_tokens": 120,
    "temperature": 0.0,
    "system_prompt_file": str(ROOT / "prompts" / "system.txt"),
    "base_url": "https://openrouter.ai/api/v1",
    "app_name": "vinted-bot",
    "app_url": "http://localhost",
}

OCR = {
    "languages": ["de", "en", "it"],
    "min_chars_for_valid": 10,
    "max_image_dim": 1600,
    "no_text_message": "Keine lesbaren Texte auf den Bildern erkannt.",
}

SCRAPER = {
    "request_delay_seconds": 1.5,
    "request_timeout": 20,
    "impersonate": "chrome124",
    "base_url": "https://www.vinted.de",
}

PATHS = {
    "db": str(ROOT / "vinted.sqlite"),
    "images": str(ROOT / "images"),
}
