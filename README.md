# book-opportunity-scraping

**Tier:** B (catalog label; Big Loop target L3) · legacy: superseded by the domain data products, see `PRODUCT.md`  
**Owner path:** `bookchaowalit/book-apps/tools/book-opportunity-scraping`

## Purpose

Loose bag of opportunity/market scrape scripts (crypto, DeFi, FX, flights, SEO, stocks, FB local, AI tools).

## Entry points

| Script | What it collects | Output (git-ignored) |
| --- | --- | --- |
| `opportunities/scrape_money_opportunities.py` | HN, GitHub, Reddit/Etsy/eBay via search, scored opportunities | `opportunities/data/` |
| `scrape_ai_tools.py` | AI tool directories | `data/book-ai/` |
| `scrape_crypto_prices.py`, `scrape_defi_yields.py`, `scrape_exchange_rates.py`, `scrape_stock_prices.py` | market prices/yields | `data/book-finance/` |
| `scrape_flight_prices.py` | flight prices for fixed routes | `data/book-travel/` |
| `scrape_seo_rankings.py` | search rankings for a domain | `data/book-marketing/` |
| `scrape_fb_local.py` | job posts in Facebook groups via search (see privacy note) | `data/contact_emails.json` |

## Stack

Python 3.10+ scripts at the repository root; dependencies in `requirements.txt`.

## How to run (local)

```bash
# From this repository root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scrape_crypto_prices.py --help
python3 scrape_flight_prices.py --routes BKK-SIN,BKK-TYO
python3 opportunities/scrape_money_opportunities.py --help
```

All scripts now resolve paths from this repository (the old monorepo
`parents[4]` lookup crashed every script on import in a standalone clone).
`scrape_money_opportunities.py` keeps its SQLite action tracker disabled (the
control-plane database it used was retired) and merges the dashboard JSON under
this repository's `data/briefings/`.

## Privacy and crawling (honest)

- `scrape_fb_local.py` harvests non-generic (i.e. likely personal) e-mail
  addresses from Facebook group posts found via Bing. Console/cron output now
  masks them (`j***@domain`) and the contact file stays in git-ignored
  `data/`, but the collection itself is a PDPA/Facebook-ToS risk; see
  `docs/UPGRADE-PLAN.md` P0.
- Several scripts send browser-like User-Agents and scrape search-engine HTML
  (DuckDuckGo/Bing/Brave/Google). Requests have timeouts; there is no shared
  retry/backoff or robots.txt handling yet.
- Runtime data (`opportunities/data/`, `data/`) and `cron.log` are not
  committed.

## Checks (offline)

With [uv](https://docs.astral.sh/uv/) and the committed `uv.lock`:

```bash
uv sync --frozen --all-extras      # runtime deps + dev tools (pytest, ruff, mypy) + sentry extra
uv run ruff check . && uv run ruff format --check .
uv run mypy .                      # gradual config in pyproject.toml
uv run pytest -q --cov             # CI gate: total coverage >= 42%
```

`requirements.txt` is kept in sync with `pyproject.toml` for the pip path above.
Error reporting is opt-in: with the `sentry` extra and `SENTRY_DSN` set, crashes,
non-zero exits and failed aggregator sources are reported (scrubbed; see `PRODUCT.md`).

Tests cover scoring, keyword matching, dedupe, route parsing, e-mail
masking, and fixture replays of HN, GitHub, DeFiLlama, CoinGecko, Frankfurter
and the ProductHunt / TAAFT / Skyscanner markdown parsers, all without network
access; CI (`.github/workflows/ci.yml`) runs them.

The crypto, FX, flight and AI-tool scripts write their CSV snapshots and
histories atomically (`atomic_io.py`: temp file + fsync + `os.replace`), so a
killed cron run never leaves a truncated file. FX history skips duplicate
`(date, base, currency)` rows, and the crypto/FX/flight CLIs validate ids,
currency codes and thresholds before any request.

## Boundaries

- **Not** a lake-first data product. Durable market datasets live under `book-*-data` repos.
- **Not** coupled to Solo Empire monorepo runtime. Nested Git repo; commit only inside this tree.
- Never commit `.env`, cookies, session dumps, or scraped PII dumps to Git.

## Limitations (honest)

Not a unified product. Prefer dedicated *-data lake products for durable datasets. Do not commit API keys.

## Related

- Active collection product: `book-job-scraping` (Tier A tool)
- Lake products: `book-crypto-data`, `book-fx-data`, `book-stock-data`, …
- Solo Empire catalog: `repository-catalog/BOOK-DEV-BACKLOG-BD.md` (BD-012)
