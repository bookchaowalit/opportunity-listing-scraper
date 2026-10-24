---
title: KPI and Instrumentation Plan — book-opportunity-scraping
created: 2026-10-22
updated: 2026-10-22
status: draft
template: architecture-docs/templates/sdlc/kpi-and-instrumentation-plan.md
---

# book-opportunity-scraping — KPI and Instrumentation Plan

Honest scope: a legacy, unscheduled repo whose market scripts are superseded and whose
roadmap goal is a recorded disposition (archive or a named remaining lane). Its KPIs
therefore measure the safe wind-down, plus run health if the aggregator is kept.

## Document control

| Field | Value |
|---|---|
| Project / product ID | book-opportunity-scraping (catalog), repo `opportunity-listing-scraper` |
| Version | 0.1 |
| Status | draft |
| Metric owner | bookchaowalit (owner) |
| AI maker | Claude session b-data, 2026-10-22 |
| AI reviewer | not yet reviewed [ต้องยืนยัน] |
| Charter objectives | Roadmap `data-scrapers.yaml` goals os-g1..os-g4 (successor mapping, boundary violations removed, no runtime data in Git, disposition recorded) |
| Analytics / data source of truth | Repo state (Git, CI), `opportunities/data/source_health.json` per run, Sentry events (opt-in, no DSN yet) |
| Dashboard | none [ต้องยืนยัน] |
| Next review | at the disposition decision (os-g4) |

## KPI tree

```text
OBJ-01 Retire the legacy scraper without losing a consumer
  └─ KPI-O-01 Entry points with a recorded successor or drop
       ├─ KPI-L-01 Boundary-violating side effects left in code
       └─ KPI-G-01 Consumers still reading legacy CSVs (must reach 0)
OBJ-02 If kept: aggregator runs are not silently broken
  └─ KPI-O-02 Successful aggregator runs
       ├─ KPI-L-02 Source failure rate per run
       └─ KPI-G-02 Snapshots overwritten by an all-failed run (must stay 0)
```

## KPI definitions

| KPI ID | Type | Name | Objective | Formula | Unit | Min volume | Segment | Data source | Baseline | Target | Alert threshold | Cadence | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KPI-O-01 | outcome | Entry points mapped | OBJ-01 | entry points with a successor/drop row / all entry points | % | n/a | all 9 | `tests/test_successor_map.py` (CI) | 100% (9/9, 2026-10-22) | 100% kept | < 100% fails CI | every push | owner |
| KPI-L-01 | leading | Side effects left | OBJ-01 | count of: Todoist push, Telegram digest, FB contact harvesting, crontab installer | count | n/a | code | `rg -n -i 'todoist|contact_emails|crontab'` | 4 (2026-10-22) | 0 by the disposition date [ต้องยืนยัน] | — | at review | owner |
| KPI-G-01 | guardrail | Legacy CSV consumers | OBJ-01 | consumers reading `money_opportunities*.csv` or `data/book-*` | count | n/a | all repos | consumer search (roadmap open question) | not yet measured [ต้องยืนยัน] | 0 before archive | — | at review | owner |
| KPI-O-02 | outcome | Successful aggregator runs | OBJ-02 | runs exiting 0 / runs | % | >= 7 runs | if kept | exit code, Sentry `error` events | not applicable: not scheduled | >= 95% [ต้องยืนยัน] | 2 consecutive failures | weekly | owner |
| KPI-L-02 | leading | Source failure rate | OBJ-02 | failed sources / requested sources per run | % | >= 5 sources | per source | `source_health.json`, Sentry `warning` events | not yet measured | < 20% [ต้องยืนยัน] | any source failing 3 runs in a row | per run | owner |
| KPI-G-02 | guardrail | Snapshots wiped by a total outage | OBJ-02 | all-failed runs that replaced the snapshot | count | n/a | — | SPEC-001 AC-01 test | 0 (behaviour fixed 2026-10-22) | must stay 0 | any > 0 | every push | owner |

## Event and data specification

| Event / field | Trigger | Properties | Personal data? | Emitted by | Requirement | Status |
|---|---|---|---|---|---|---|
| Sentry "money-opportunities: N of M sources failed: …" | a run with failed sources | level, source names + status, tag `job` | no | `observability.report_source_failures` | SPEC-001 AC-01/02 | implemented, not live |
| Sentry "<job> crashed: <Type>" / "<job> exited with code N" | crash or non-zero exit of any entry point | tags `job`, `exc_type` | no (scrubbed; AC-05) | `observability.run_job` | SPEC-001 AC-02/05 | implemented, not live |
| `source_health.json` | every aggregator run | source, status, items, duration, error text | error text may hold URLs (local file only) | aggregator | — | implemented |

Privacy: `scrape_fb_local.py` handles e-mail addresses (personal data under PDPA); it is a
drop pending owner disposition and nothing from it is sent to Sentry.

## Dashboards and alerts

| Dashboard / alert | KPIs | Audience | Location | Refresh | Alert channel | Status |
|---|---|---|---|---|---|---|
| Sentry issue stream | KPI-O-02, KPI-L-02 | owner | Sentry (project not created) | live | Sentry email [ต้องยืนยัน] | planned, only if kept |

## Instrumentation verification (before G10)

| # | Check | Evidence | Result |
|---|---|---|---|
| 1 | Each failure sends one event | `tests/test_run_failures.py`, `tests/test_observability.py` (fake SDK) | pass (offline) |
| 2 | Counts reconcile with `source_health.json` | same tests | pass (offline) |
| 3 | No PII/secrets in events | AC-05 scrub tests | pass |
| 4 | Dashboard | — | not started |
| 5 | Alert reaches owner | needs Sentry project + DSN (owner action) | not started |
| 6 | Baselines | live baselines need scheduled runs | waived: repo is unscheduled and archive-bound |
| 7 | Consent | n/a (no end users) | n/a |

## Change history of definitions

| Date | KPI ID | Change | Reason | Baseline restated? | Approved by |
|---|---|---|---|---|---|
| 2026-10-22 | all | first draft | Big Loop L3 | n/a | pending |

## Review (2026-10-24): changes requested

Checker: independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context). Status unchanged until fixed.

- Gap: KPI-L-01 baseline of 4 side effects is not reproducible with the stated command rg -i 'todoist|contact_emails|crontab' (Telegram missing from the pattern; finds 3).
