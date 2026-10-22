"""``observability.run_job`` wraps every root script's entry point.

An uncaught exception or a non-zero ``sys.exit`` from a cron-run script was only
visible in a log file nobody reads. With ``SENTRY_DSN`` set, the wrapper sends
the exception (or one message for the exit code) and re-raises unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from observability import init_sentry, run_job  # noqa: E402
from test_run_failures import FakeSentry  # noqa: E402


@pytest.fixture
def fake_sentry(monkeypatch):
    sdk = FakeSentry()
    monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    return sdk


def test_uncaught_exception_is_captured_and_reraised(fake_sentry):
    def main():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        run_job("crypto-prices", main)
    assert fake_sentry.tags == {"job": "crypto-prices"}
    assert fake_sentry.init_kwargs is not None
    assert fake_sentry.init_kwargs["environment"] == "test"
    assert [level for level, _ in fake_sentry.messages] == ["exception"]


def test_non_zero_exit_is_reported_and_kept(fake_sentry):
    def main():
        sys.exit(1)

    with pytest.raises(SystemExit) as info:
        run_job("stock-prices", main)
    assert info.value.code == 1
    assert fake_sentry.messages == [("error", "stock-prices exited with code 1")]


def test_returned_exit_code_is_reported(fake_sentry):
    assert run_job("money-opportunities", lambda: 1) == 1
    assert fake_sentry.messages == [("error", "money-opportunities exited with code 1")]


def test_success_sends_nothing(fake_sentry):
    assert run_job("fx-rates", lambda: None) == 0
    with pytest.raises(SystemExit):
        run_job("fx-rates", lambda: sys.exit(0))
    assert fake_sentry.messages == []


def test_without_dsn_nothing_is_initialised(fake_sentry, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN")
    assert init_sentry("x") is None
    with pytest.raises(ValueError):
        run_job("x", lambda: (_ for _ in ()).throw(ValueError("boom")))
    assert fake_sentry.init_kwargs is None
