# vinted-bot

Arbitrage classifier for Vinted.de. Scrapes catalog listings, runs OCR on item photos, sends a structured prompt to an LLM against a user-defined rule set, and exposes a local dashboard for triage.

## How it works

1. Fetches a Vinted catalog page anonymously using a browser-impersonating HTTP client.
2. For each item: downloads photos and runs EasyOCR (de, en, it) for patch and tag text, scrapes the HTML page for description and actual shipping cost.
3. Builds a prompt with OCR text, item metadata, buyer protection and shipping, plus the description. Sends to Claude Haiku 4.5 via OpenRouter.
4. Parses the reply as `ja` or `nein: <reason>` and stores everything in SQLite.
5. FastAPI dashboard shows approved items for triage and rejected items with their rejection reason.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate           # or activate.fish
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...
```

First run downloads ~1 GB of EasyOCR models, one time only.

## Configuration

Everything in `config.py`:

- `SEARCH_URL`: paste a Vinted catalog URL with UI filters applied; query params are translated to the API format
- `SEARCH_OVERRIDES`: manual parameter overrides (price, page, per_page, ...)
- `MAX_ITEMS_PER_RUN`: cap per run for testing
- `CLASSIFIER.model`: OpenRouter model id

The classification rules live in `prompts/system.txt` and define what counts as "interesting".

## Run

```sh
python3 run.py                              # scrape + classify
uvicorn dashboard.app:app --reload          # dashboard on localhost:8000
```

To re-classify everything after changing the prompt:

```sh
rm vinted.sqlite
python3 run.py
```

## Layout

```
config.py              # all settings
run.py                 # entrypoint
prompts/system.txt     # LLM rules (user-edited)
scraper/               # Vinted session, catalog API, HTML scrape, filter parsing
pipeline/              # image download, OCR, prompt builder, classifier
storage/               # SQLite schema and helpers
dashboard/             # FastAPI + Jinja templates
scripts/               # debug helpers
```
