# vinted-bot

Arbitrage classifier for Vinted.de. Scrapes catalog listings, runs OCR on item photos, sends a structured prompt to an LLM against a user-defined rule set, and exposes a local dashboard for triage.

## How it works

1. Fetches a Vinted catalog page anonymously using a browser-impersonating HTTP client.
2. For each item: downloads photos, runs EasyOCR (de, en, it) on them, scrapes the HTML for description and shipping cost.
3. Builds a prompt with OCR text, item metadata, buyer protection and shipping, plus the description. Sends to Claude Haiku 4.5 via OpenRouter.
4. Parses the reply as `ja`, `vielleicht: <reason>` or `nein: <reason>` and stores everything in SQLite.
5. FastAPI dashboard shows approved items for triage and rejected ones with their rejection reason.

## Run it (no terminal)

For users who do not want to touch the command line.

1. Download [`vinted-bot.command`](https://github.com/yungweng/vinted-bot/raw/main/vinted-bot.command).
2. Put your OpenRouter key in `~/.config/vinted-bot/env`:
   ```
   export OPENROUTER_API_KEY=sk-or-...
   ```
3. Double-click `vinted-bot.command`. First launch installs uv and dependencies (a few minutes, mostly PyTorch). Subsequent launches start in seconds and pull the latest code automatically.
4. The dashboard opens in your browser at `http://127.0.0.1:<port>`.

Data lives in `~/Library/Application Support/vinted-bot/`.

## Run it (developer)

```sh
git clone https://github.com/yungweng/vinted-bot
cd vinted-bot
uv sync
export OPENROUTER_API_KEY=sk-or-...

uv run vinted-bot scrape    # one classification run
uv run vinted-bot serve     # dashboard
```

Or install once and call directly:

```sh
uv tool install .
vinted-bot scrape
vinted-bot serve
```

## Configuration

Everything in `src/vinted_bot/config.py`:

- `SEARCH_URL`: paste a Vinted catalog URL with UI filters applied; query params get translated to the API format
- `SEARCH_OVERRIDES`: manual parameter overrides (price, page, per_page, ...)
- `MAX_ITEMS_PER_RUN`: cap per run for testing
- `CLASSIFIER.model`: OpenRouter model id

The classification rules live in `src/vinted_bot/prompts/system.txt`.

## Layout

```
pyproject.toml                          # package metadata, deps, entry point
vinted-bot.command                      # double-click launcher (macOS)
src/vinted_bot/
  cli.py                                # entry point: serve | scrape
  config.py                             # all settings
  scrape.py                             # scrape + classify loop
  prompts/system.txt                    # LLM rules (user-edited)
  scraper/                              # Vinted session, catalog API, HTML scrape, filter parsing
  pipeline/                             # image download, OCR, prompt builder, classifier
  storage/                              # SQLite schema and helpers
  dashboard/                            # FastAPI + Jinja templates
scripts/                                # debug helpers
```
