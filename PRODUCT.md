# Opportunity listing scraper — successor mapping

Canonical repository: `bookchaowalit/opportunity-listing-scraper` (formerly
`book-opportunity-scraping`). GitHub alias metadata on 2026-10-15 resolves to
this public, unarchived repository. The mapping below covers all eight root
`scrape_*.py` scripts and the aggregator at source commit
`7d135c1bf44e57f99c38f8e54f1f6e79920ab138`.

**Catalog tier:** B (Big Loop target L3) · **Updated:** 2026-10-22 · **Disposition:** legacy,
archive candidate once consumers are verified (roadmap goal os-g4, owner decision)

## Runtime status (verified 2026-10-22)

| What | Status |
|---|---|
| Entry points | 7 root `scrape_*.py` scripts (`scrape_flight_prices.py` was removed on 2026-10-23) and `opportunities/scrape_money_opportunities.py`; each `__main__` runs through `observability.run_job` |
| Which ones run | None on a schedule. They run only when invoked by hand; five market scripts are superseded by the domain products below, which own capture today; `scrape_ai_tools.py` has no successor since the AI tools product was retired on 2026-10-23, and the flights product was retired the same day, so its scraper was removed |
| Who schedules it | Nothing in this repo is installed. There is no `setup_cron.sh`; the aggregator's `--setup-cron` flag can append a daily 10:00 crontab line (with `--send-digest --push-todoist`). This WSL host's crontab has no entry for it on 2026-10-22; Windows Task Scheduler cannot be checked from WSL [ต้องยืนยัน] |
| Hosted deployment | None. No port, no API, no cloud job; not part of the frozen `data-product-contracts-v4` port map (8101-8104 and 8106 belong to the successors; 8105 and 8107 were retired with the flights and AI tools products on 2026-10-23 and are never reused) |
| Error reporting | Sentry, opt-in: install the `sentry` extra and set `SENTRY_DSN`. Crashes are sent as the exception type plus tags, non-zero exits as one event, and failed aggregator sources as one event naming the sources (no error text). Locals, request bodies, breadcrumbs and exception messages are scrubbed. No DSN is configured [ต้องยืนยัน] |
| Failure behaviour | If every aggregator source fails, the previous `money_opportunities.csv` snapshot is kept and the run exits 1 |
| Side effects still in code | Telegram digest (`--send-digest`), Todoist push (`--push-todoist`) and `scrape_fb_local.py` contact-email harvesting; all opt-in, none removed by this change (roadmap os-t2) |
| Contract | None of its own: CSV outputs under git-ignored `data/` and `opportunities/data/`, no lake landing. `tests/test_successor_map.py` keeps the table below complete |
| Quality gates in CI | ruff, ruff format, mypy (gradual; strict on `observability.py`), offline pytest with coverage >= 42%, on Python 3.10 and 3.13, plus the shared security scan |

## Successors

| Legacy entry point | Successor or explicit drop | Contract / boundary |
|---|---|---|
| `scrape_crypto_prices.py` | [`market-data/sources/crypto`](https://github.com/bookchaowalit/market-data/tree/main/sources/crypto) (formerly `book-crypto-data`) | `book_crypto`, `crypto.v1`; source-owned landing/Bronze and read-only API |
| `scrape_stock_prices.py` | [`market-data/sources/stock`](https://github.com/bookchaowalit/market-data/tree/main/sources/stock) (formerly `book-stock-data`) | `book_stock`, `stock.v1` |
| `scrape_exchange_rates.py` | [`market-data/sources/fx`](https://github.com/bookchaowalit/market-data/tree/main/sources/fx) (formerly `book-fx-data`) | `book_fx`, `fx.v1` |
| `scrape_defi_yields.py` | [`market-data/sources/defi`](https://github.com/bookchaowalit/market-data/tree/main/sources/defi) (formerly `book-defi-data`) | `book_defi`, `defi.v1` |
| `scrape_flight_prices.py` | **Drop: product retired, script removed.** The former successor `travel-flight-price-data` (`book_flight`, `flight.v1` on :8105) was retired on 2026-10-23 in `data-product-contracts-v4.yaml` and is to be archived; the script, its fixture and tests were deleted | No flights data product exists any more; nothing here scrapes flight prices |
| `scrape_seo_rankings.py` | [`marketing-seo-ranking-data`](https://github.com/bookchaowalit/marketing-seo-ranking-data) (formerly `book-seo-data`) | `book_seo`, `seo.v1` |
| `scrape_ai_tools.py` | **Drop: product retired.** The former successor `tech-ai-tools-data` (`book_ai_tools`, `ai_tools.v1` on :8107) was retired on 2026-10-23 in `data-product-contracts-v3.yaml` and is to be archived | No AI tools data product exists any more; this mapping does not approve collection or scheduling |
| `scrape_fb_local.py` | **Drop from the successor plan**; no approved domain contract replaces personal-contact harvesting | Existing code remains pending its separate owner disposition in `docs/UPGRADE-PLAN.md`; this mapping does not approve collection, outreach or scheduling |
| `opportunities/scrape_money_opportunities.py` | **Drop cross-domain synthesis**; no replacement mega-aggregator | Architecture retires synthesis. Technology signals belong to [`tech-discovery-data`](https://github.com/bookchaowalit/tech-discovery-data) / `discovery.v1`; other opportunities use their owning domain contracts |

## Migration sequence and limits

This follows the canonical architecture's
[Data Product Portfolio migration order](https://github.com/bookchaowalit/architecture-docs/blob/a550ade4c40592e6f8416b5ee52d603357733629/systems/architecture/data-product-portfolio.md):

1. Retain the coverage registry as inventory; source adapters belong to their
   domain product. Establish its schema and fixtures before moving code.
2. Use the five independently runnable source products above (AI tools and flights retired 2026-10-23); keep
   `opportunities/` as human-facing inventory/research, with executable
   discovery in domain products and the shared portfolio CLI.
3. Migrate consumers through APIs, CLIs, exports or versioned packages, then
   verify no direct reads of legacy paths remain.
4. Register the resulting repository and source path before removing or
   deprecating an old implementation.

This is a successor plan, not evidence of completed consumer migration or an
archive decision. The legacy scripts, the aggregator's optional Todoist side effect
and its `--setup-cron` installer flag still exist; none was run, removed or enabled by this work.
The existing tests remain offline and do not approve live providers. See
`README.md` for their checks and `docs/UPGRADE-PLAN.md` for remaining work.

## Docs

- Spec: `specs/001-l2-baseline/spec.md` · KPI plan: `docs/measurement/KPI-PLAN.md`
