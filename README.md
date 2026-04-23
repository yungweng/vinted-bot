# vinted-bot

Arbitrage classifier for Vinted.de. Scrapes catalog listings, runs OCR on item photos, sends a structured prompt to an LLM against a user-defined rule set, and exposes a local dashboard for triage.

## How it works

1. Fetches a Vinted catalog page anonymously using a browser-impersonating HTTP client.
2. For each item: downloads photos, runs EasyOCR (de, en, it) on them, scrapes the HTML for description and shipping cost.
3. Builds a prompt with OCR text, item metadata, buyer protection and shipping, plus the description. Sends to the configured model via OpenRouter.
4. Parses the reply as `ja`, `vielleicht: <reason>` or `nein: <reason>` and stores everything in SQLite.
5. FastAPI dashboard groups results per search — approved items for triage, rejected items with their reasons.

## Run it (no terminal)

For users who do not want to touch the command line.

1. Download [`vinted-bot.command`](https://github.com/yungweng/vinted-bot/raw/main/vinted-bot.command).
2. Double-click `vinted-bot.command`. First launch installs uv and dependencies (a few minutes, mostly PyTorch). Subsequent launches start in seconds.
3. The dashboard opens in your browser at `http://127.0.0.1:<port>`.
4. Open **Einstellungen** and paste your OpenRouter API key. Save. Done.
5. Click **Neue Suche**, paste a Vinted URL with your filters, hit "Suche starten".

Data lives in `~/Library/Application Support/vinted-bot/`.

## Run it (developer)

```sh
git clone https://github.com/yungweng/vinted-bot
cd vinted-bot
uv sync
uv run vinted-bot
```

Or install once and call directly:

```sh
uv tool install .
vinted-bot
```

## Dashboard

The dashboard has three pages:

- **Neue Suche**: paste a Vinted link with filters, adjust rules, start a run. Scrape runs in the background.
- **Verlauf**: all past searches with counts per verdict. Click one to see items, tabs for `ja` / `vielleicht` / `nein` / `entschieden`.
- **Einstellungen**: OpenRouter API key, model, max entries, default prompts. Also has a "Datenbank zurücksetzen" button that wipes all searches and items (keeps config).

## Prompt structure

Each search has four rule sections, merged into one system prompt:

- **Ja**: criteria that accept the item
- **Nein**: criteria that reject the item
- **Vielleicht**: uncertainty fallback
- **Sonderregeln**: things not obviously in the above

Defaults are editable in Einstellungen and prefill every new search.

## CSS build (dev only)

The dashboard ships a pre-built `output.css`. If you change templates or `input.css`, rebuild with the Tailwind v4 standalone binary:

```sh
# One-time: download from https://github.com/tailwindlabs/tailwindcss/releases/latest
TAILWIND_BIN=./tailwindcss ./scripts/build_css.sh
```

## Layout

```
pyproject.toml                          # package metadata, deps, entry point
vinted-bot.command                      # double-click launcher (macOS)
src/vinted_bot/
  cli.py                                # entry point: serve (default)
  config.py                             # OCR/scraper/paths only — everything user-facing is in DB
  scrape.py                             # scrape + classify, invoked per search from the dashboard
  prompts/default_*.txt                 # defaults seeded into app_config on first run
  scraper/                              # Vinted session, catalog API, HTML scrape, filter parsing
  pipeline/                             # image download, OCR, prompt builder, classifier
  storage/                              # SQLite schema + CRUD
  dashboard/
    app.py                              # FastAPI routes
    templates/                          # Jinja2 templates
    static/                             # Tailwind + basecoat CSS (pre-built)
scripts/
  build_css.sh                          # rebuild Tailwind output
```
