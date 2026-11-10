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

from observability import (  # noqa: E402
    init_sentry,
    report_source_failures,
    run_job,
    scrub_event,
)
from test_run_failures import (  # noqa: E402
    FakeLoggingIntegration,
    FakeSentry,
    install_fake_logging_integration,
)

SECRET = "token=abc123"


@pytest.fixture
def fake_sentry(monkeypatch):
    sdk = FakeSentry()
    monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
    install_fake_logging_integration(monkeypatch)
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    return sdk


def test_uncaught_exception_is_reported_by_type_only_and_reraised(fake_sentry):
    def main():
        raise ValueError("token=abc123 in https://example.test/secret")

    with pytest.raises(ValueError):
        run_job("crypto-prices", main)
    assert fake_sentry.tags == {"job": "crypto-prices", "exc_type": "ValueError"}
    assert fake_sentry.init_kwargs is not None
    assert fake_sentry.init_kwargs["environment"] == "test"
    # Type name only: the exception message can carry tokens or source bodies.
    assert fake_sentry.messages == [("error", "crypto-prices crashed: ValueError")]


def test_init_disables_locals_and_request_bodies(fake_sentry):
    init_sentry("x")
    kwargs = fake_sentry.init_kwargs
    assert kwargs is not None
    assert kwargs["include_local_variables"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["send_default_pii"] is False
    assert callable(kwargs["before_send"])


def test_before_send_strips_frame_vars_request_and_messages(fake_sentry):
    init_sentry("x")
    assert fake_sentry.init_kwargs is not None
    before_send = fake_sentry.init_kwargs["before_send"]
    event = {
        "message": "boom",
        "request": {"url": "https://example.test/?token=abc", "data": "body"},
        "breadcrumbs": {"values": [{"message": "GET https://example.test/?token=abc"}]},
        "extra": {"payload": "body"},
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "token=abc123",
                    "stacktrace": {
                        "frames": [{"function": "main", "vars": {"token": "abc123"}}]
                    },
                }
            ]
        },
        "threads": {"values": [{"stacktrace": {"frames": [{"vars": {"body": "x"}}]}}]},
    }
    cleaned = before_send(event, {})
    assert "request" not in cleaned
    assert "breadcrumbs" not in cleaned
    assert "extra" not in cleaned
    value = cleaned["exception"]["values"][0]
    assert value["type"] == "ValueError"
    assert value["value"] == ""
    assert "vars" not in value["stacktrace"]["frames"][0]
    assert "vars" not in cleaned["threads"]["values"][0]["stacktrace"]["frames"][0]
    assert "abc123" not in repr(cleaned)


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


def test_init_disables_log_to_event_and_breadcrumbs(fake_sentry: FakeSentry) -> None:
    # The default LoggingIntegration turns logger.error(...) (ours or a library's)
    # into an event whose logentry holds free log text: URLs, bodies, tokens.
    init_sentry("x")
    assert fake_sentry.init_kwargs is not None
    found = [
        i
        for i in fake_sentry.init_kwargs["integrations"]
        if isinstance(i, FakeLoggingIntegration)
    ]
    assert len(found) == 1
    assert found[0].kwargs["event_level"] is None
    assert found[0].kwargs["level"] is None
    assert found[0].kwargs["sentry_logs_level"] is None


def test_before_send_drops_logentry():
    text = f"GET https://example.test/?{SECRET} failed"
    event = {"logentry": {"message": text, "formatted": text, "params": [SECRET]}}
    cleaned = scrub_event(event, {})
    assert "logentry" not in cleaned
    assert "abc123" not in repr(cleaned)


def test_before_send_drops_foreign_message():
    for foreign in (
        f"request to https://example.test/?{SECRET}",
        f"crypto-prices crashed: ValueError {SECRET}",
        "crypto-prices exited with code 1 extra",
        "money-opportunities: 1 of 2 sources failed: github (HTTP 503 at /x)",
    ):
        assert "message" not in scrub_event({"message": foreign}, {})


def test_before_send_keeps_own_reporter_messages(fake_sentry):
    with pytest.raises(ValueError):
        run_job("crypto-prices", lambda: (_ for _ in ()).throw(ValueError(SECRET)))
    with pytest.raises(SystemExit):
        run_job("stock-prices", lambda: sys.exit("fatal: " + SECRET))
    run_job("money-opportunities", lambda: 2)
    sdk = init_sentry("money-opportunities")
    report_source_failures(
        sdk,
        "money-opportunities",
        [
            {"source": "hn", "status": "ok"},
            {"source": "github", "status": "error"},
            {"source": "reddit", "status": "timeout"},
        ],
    )
    own = [message for _, message in fake_sentry.messages]
    assert own == [
        "crypto-prices crashed: ValueError",
        "stock-prices exited with code 1",
        "money-opportunities exited with code 2",
        "money-opportunities: 2 of 3 sources failed: github (error), reddit (timeout)",
    ]
    for message in own:
        assert scrub_event({"message": message}, {})["message"] == message


def test_before_send_blanks_exception_value():
    event = {"exception": {"values": [{"type": "ValueError", "value": SECRET}]}}
    assert scrub_event(event, {})["exception"]["values"][0]["value"] == ""
