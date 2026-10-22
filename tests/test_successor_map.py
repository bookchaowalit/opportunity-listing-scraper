"""PRODUCT.md's successor table must cover every legacy entry point.

The seven root market scripts are superseded by the domain products frozen in
``data-product-contracts-v2.yaml`` (ports 8101-8107); that registry lives in the
private architecture-docs repository, so the mapping below is a copy taken on
2026-10-22. A new ``scrape_*.py`` without a row in PRODUCT.md fails here.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = (ROOT / "PRODUCT.md").read_text(encoding="utf-8")

# v2 product id -> (port, legacy script it replaces)
V2_SUCCESSORS = {
    "crypto": (8101, "scrape_crypto_prices.py"),
    "stocks": (8102, "scrape_stock_prices.py"),
    "fx": (8103, "scrape_exchange_rates.py"),
    "defi": (8104, "scrape_defi_yields.py"),
    "flights": (8105, "scrape_flight_prices.py"),
    "seo": (8106, "scrape_seo_rankings.py"),
    "ai_tools": (8107, "scrape_ai_tools.py"),
}
DROPPED = {"scrape_fb_local.py", "opportunities/scrape_money_opportunities.py"}


def _table_rows() -> dict[str, str]:
    rows = {}
    for line in PRODUCT.splitlines():
        match = re.match(r"\|\s*`([^`]+\.py)`\s*\|(.*)", line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def test_every_entry_point_has_a_successor_row():
    scripts = {p.name for p in ROOT.glob("scrape_*.py")}
    scripts |= {f"opportunities/{p.name}" for p in (ROOT / "opportunities").glob("scrape_*.py")}
    assert scripts - set(_table_rows()) == set()


def test_each_v2_product_replaces_exactly_one_script():
    scripts = [script for _port, script in V2_SUCCESSORS.values()]
    assert len(scripts) == len(set(scripts)) == 7
    rows = _table_rows()
    for script in scripts:
        assert "**Drop" not in rows[script], script


def test_dropped_entry_points_are_marked_as_drops():
    rows = _table_rows()
    for script in DROPPED:
        assert "**Drop" in rows[script], script
