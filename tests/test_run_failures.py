"""Failed sources in the money-opportunities run must not stay silent.

The aggregator catches every source exception, logs it to the console and keeps
going. Two consequences, both silent under cron:

* a run where every source failed still overwrote ``money_opportunities.csv``
  with an empty snapshot (wiping the previous one and the next run's score
  deltas) and exited 0;
* nothing outside the console log said that sources were failing.

With ``SENTRY_DSN`` set, a run with failed sources sends one event naming the
failed sources (names and status only: the error text can hold URLs). A fake
``sentry_sdk`` module stands in for the SDK; sources are fakes, no network.
"""

from __future__ import annotations

import csv
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "opportunities"))

import scrape_money_opportunities as money  # noqa: E402


class FakeSentry(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("sentry_sdk")
        self.init_kwargs: dict[str, Any] | None = None
        self.messages: list[tuple[str, str]] = []
        self.tags: dict[str, str] = {}

    def init(self, **kwargs: Any) -> None:
        self.init_kwargs = kwargs

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value

    def capture_message(self, message: str, level: str = "info") -> None:
        self.messages.append((level, message))

    def capture_exception(self, error: BaseException | None = None) -> None:
        self.messages.append(("exception", repr(error)))

    def flush(self, timeout: float | None = None) -> None:
        pass


@pytest.fixture
def fake_sentry(monkeypatch):
    sdk = FakeSentry()
    monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    return sdk


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    out = tmp_path / "opportunities" / "data"
    monkeypatch.setattr(money, "OUTPUT_DIR", out)
    monkeypatch.setattr(money, "SOURCE_HEALTH_FILE", out / "source_health.json")
    monkeypatch.setattr(money, "ROOT", tmp_path)
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)
    return out


def _ok():
    return [
        {
            "title": "AI prompt pack for Etsy sellers",
            "url": "https://example.test/1",
            "source": "hn",
            "price": "",
            "notes": "",
        }
    ]


def _boom():
    raise RuntimeError("HTTP 503 for https://example.test/secret-query?q=token")


def _run(sources: dict, monkeypatch) -> Any:
    names = ",".join(sources)
    monkeypatch.setattr(
        sys, "argv", ["scrape_money_opportunities.py", "--sources", names]
    )
    with patch.dict(money.SOURCE_MAP, sources, clear=True):
        return money.main()


def _write_previous_snapshot(out: Path) -> str:
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "money_opportunities.csv"
    snapshot.write_text("title,trend_score\nPrevious idea,77\n", encoding="utf-8")
    return snapshot.read_text(encoding="utf-8")


def test_all_sources_failing_keeps_the_previous_snapshot_and_exits_1(
    fake_sentry, sandbox, monkeypatch
):
    before = _write_previous_snapshot(sandbox)
    code = _run({"hn": ("HN", _boom), "github": ("GitHub", _boom)}, monkeypatch)
    assert code == 1
    assert (sandbox / "money_opportunities.csv").read_text(encoding="utf-8") == before
    assert [level for level, _ in fake_sentry.messages] == ["error"]
    message = fake_sentry.messages[0][1]
    assert "2 of 2" in message and "github" in message and "hn" in message
    assert "secret-query" not in message


def test_partial_failure_reports_a_warning_and_still_saves(
    fake_sentry, sandbox, monkeypatch
):
    code = _run({"hn": ("HN", _ok), "github": ("GitHub", _boom)}, monkeypatch)
    assert code in (0, None)
    assert fake_sentry.init_kwargs is not None
    assert fake_sentry.init_kwargs["send_default_pii"] is False
    assert fake_sentry.init_kwargs["traces_sample_rate"] == 0.0
    assert fake_sentry.messages == [
        ("warning", "money-opportunities: 1 of 2 sources failed: github (error)")
    ]
    with (sandbox / "money_opportunities.csv").open(encoding="utf-8") as handle:
        assert [row["title"] for row in csv.DictReader(handle)] == [
            "AI prompt pack for Etsy sellers"
        ]


def test_clean_run_sends_nothing(fake_sentry, sandbox, monkeypatch):
    assert _run({"hn": ("HN", _ok)}, monkeypatch) in (0, None)
    assert fake_sentry.messages == []


def test_without_dsn_sentry_is_never_initialised(fake_sentry, sandbox, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN")
    _run({"hn": ("HN", _ok), "github": ("GitHub", _boom)}, monkeypatch)
    assert fake_sentry.init_kwargs is None
    assert fake_sentry.messages == []
