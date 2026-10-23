"""PRODUCT.md's successor table must cover every legacy entry point.

Five root market scripts are superseded by the domain products frozen in
``data-product-contracts-v4.yaml`` (ports 8101-8104 and 8106); that registry lives
in the private architecture-docs repository, so the mapping below is a copy
taken on 2026-10-23. v3 retired the ai_tools product (:8107, tech-ai-tools-data),
so ``scrape_ai_tools.py`` has no successor and is an explicit drop. v4 retired
the flights product (:8105, travel-flight-price-data), so
``scrape_flight_prices.py`` was removed and its row is an explicit drop.
A new ``scrape_*.py`` without a row in PRODUCT.md fails here.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = (ROOT / "PRODUCT.md").read_text(encoding="utf-8")

# v4 product id -> (port, legacy script it replaces)
V4_SUCCESSORS = {
    "crypto": (8101, "scrape_crypto_prices.py"),
    "stocks": (8102, "scrape_stock_prices.py"),
    "fx": (8103, "scrape_exchange_rates.py"),
    "defi": (8104, "scrape_defi_yields.py"),
    "seo": (8106, "scrape_seo_rankings.py"),
}
DROPPED = {
    "scrape_ai_tools.py",
    "scrape_flight_prices.py",
    "scrape_fb_local.py",
    "opportunities/scrape_money_opportunities.py",
}


def _table_rows() -> dict[str, str]:
    rows = {}
    for line in PRODUCT.splitlines():
        match = re.match(r"\|\s*`([^`]+\.py)`\s*\|(.*)", line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def test_every_entry_point_has_a_successor_row():
    scripts = {p.name for p in ROOT.glob("scrape_*.py")}
    scripts |= {
        f"opportunities/{p.name}" for p in (ROOT / "opportunities").glob("scrape_*.py")
    }
    assert scripts - set(_table_rows()) == set()


def test_each_v4_product_replaces_exactly_one_script():
    scripts = [script for _port, script in V4_SUCCESSORS.values()]
    assert len(scripts) == len(set(scripts)) == 5
    assert 8105 not in {port for port, _script in V4_SUCCESSORS.values()}
    rows = _table_rows()
    for script in scripts:
        assert "**Drop" not in rows[script], script


def test_dropped_entry_points_are_marked_as_drops():
    rows = _table_rows()
    for script in DROPPED:
        assert "**Drop" in rows[script], script


def test_retired_ai_tools_product_is_not_named_as_a_successor():
    successor = _table_rows()["scrape_ai_tools.py"].split("|")[0]
    assert "github.com/bookchaowalit/tech-ai-tools-data" not in successor
    assert "retired" in successor.lower()


def test_retired_flights_product_is_not_named_as_a_successor():
    successor = _table_rows()["scrape_flight_prices.py"].split("|")[0]
    assert "github.com/bookchaowalit/travel-flight-price-data" not in successor
    assert "retired" in successor.lower()


def test_flight_scraper_and_its_fixture_are_removed():
    assert not (ROOT / "scrape_flight_prices.py").exists()
    assert not (ROOT / "tests" / "fixtures" / "skyscanner_bkk_sin.md").exists()
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        if path.name == "test_successor_map.py":
            continue
        assert "scrape_flight_prices" not in path.read_text(encoding="utf-8"), path.name
