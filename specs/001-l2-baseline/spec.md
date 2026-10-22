---
id: SPEC-001
title: L2/L3 baseline for opportunity-listing-scraper
status: in review
created: 2026-10-22
owner: bookchaowalit
---

# SPEC-001: L2/L3 baseline

## Document control

| Field | Value |
|---|---|
| Main-only | yes (ADR-0004 v1.1: red run is local, red and green commits pushed together) |
| Maker | Claude session b-data (2026-10-22) |
| Checker / approver | pending (owner) |

## Problem

The Big Loop scorecard (2026-10-22) had this legacy repo at L0: no lockfile, no type
check, no error reporting, no spec or KPI plan, and `ruff format` was switched off.
Review of the aggregator found silent failures:

1. Every source exception is caught and printed. A run in which **all** sources failed
   still wrote an empty `money_opportunities.csv` over the last good snapshot (which
   also feeds the next run's score deltas) and exited 0.
2. Nothing outside a console log reported failing sources, crashes or non-zero exits of
   any of the nine entry points.

## Behaviour

1. Dependencies resolve from the committed `uv.lock` (`[tool.uv] package = false`);
   `requirements.txt` stays in sync for the pip path.
2. `mypy .` runs in CI (gradual; legacy scripts tolerate implicit Optional and bs4
   attribute types; strict on `observability.py`). Code is `ruff format`-clean.
3. When every requested aggregator source fails, the previous snapshot is kept, source
   health is still written, and `main()` returns 1 (process exit 1).
4. With `SENTRY_DSN` set and the `sentry` extra installed: a run with failed sources
   sends one event (`warning` if some failed, `error` if all) naming the sources and
   their status only; any entry point that crashes sends `"<job> crashed: <Type>"` with
   tags `job` and `exc_type`, and re-raises; a non-zero exit sends one `error` event.
   Without a DSN the SDK is never imported.
5. Sentry is initialised with `send_default_pii=False`, `traces_sample_rate=0.0`,
   `include_local_variables=False`, `max_request_body_size="never"` and a `before_send`
   (`scrub_event`) that drops frame `vars`, `request`, `breadcrumbs` and `extra` and
   blanks exception messages (security review 2026-10-22).
6. PRODUCT.md's successor table lists every entry point; the seven v2 products each
   replace exactly one script; the FB and aggregator rows are drops.
7. CI fails when total coverage drops below 42%.

## Acceptance

| AC | Given / When / Then | Test |
|---|---|---|
| AC-01 | Given a previous snapshot, when every source fails, then the snapshot is unchanged, `main()` returns 1 and one `error` event "2 of 2" is sent without the error text | `tests/test_run_failures.py::test_all_sources_failing_keeps_the_previous_snapshot_and_exits_1` |
| AC-02 | Given 1 of 2 sources fails, then one `warning` event names it and the snapshot is saved; a clean run or no DSN sends nothing; `run_job` reports crashes and non-zero exits and re-raises | `tests/test_run_failures.py`, `tests/test_observability.py` |
| AC-03 | ruff, ruff format and mypy pass | CI lint/typecheck steps |
| AC-04 | Successor table covers every entry point | `tests/test_successor_map.py` |
| AC-05 | Sentry init disables locals and request bodies; `before_send` strips vars, request, breadcrumbs, extras and exception messages; crashes are sent by type name | `tests/test_observability.py` (3 tests) |
| AC-06 | CI on `main` is green on Python 3.10 and 3.13 with the coverage gate | CI run below |

## Red/green log

| AC | Red (sha · command · failure) | Green |
|---|---|---|
| AC-01, AC-02 | `9a35c40` · `python -m pytest -q tests/test_run_failures.py tests/test_observability.py` · `ModuleNotFoundError: No module named 'observability'`; `test_run_failures.py` alone: `assert None == 1` and `assert None is not None` (init never called). Re-verified red after the 2026-10-22 machine restart | [run 39755435609](https://github.com/bookchaowalit/opportunity-listing-scraper/actions/runs/39755435609) (success, 3.10 + 3.13, `51ebcba`) |
| AC-05 | `21c1511` · `python -m pytest -q tests/test_observability.py` · `KeyError: 'include_local_variables'`, `KeyError: 'before_send'`, missing `exc_type` tag (3 failed) | [run 39755435609](https://github.com/bookchaowalit/opportunity-listing-scraper/actions/runs/39755435609) (success, 3.10 + 3.13, `51ebcba`) |

## Schedule (planned replacement, D6)

No change made. Today nothing schedules this repo: there is no `setup_cron.sh`, and the
aggregator's `--setup-cron` flag (daily 10:00 crontab line with `--send-digest
--push-todoist`) is not installed on this WSL host (checked 2026-10-22); Windows tasks
are unverified [ต้องยืนยัน]. Planned replacement: **none for this repo.** The seven
market scripts' schedules belong to their successor products (market-data, flight, SEO,
AI-tools) under D6; the aggregator and `scrape_fb_local.py` are drops. If the owner keeps
the aggregator (roadmap os-g4), it would run as one hosted daily job without
`--push-todoist` and with `SENTRY_DSN` set, after the Todoist push is removed (os-t2).

## Out of scope

Live runs, removing the Todoist push or the FB script (owner disposition), the archive
decision, consumer migration checks, and reaching the 80% coverage floor.
