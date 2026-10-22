"""Opt-in Sentry for the legacy scraper scripts.

Off unless ``SENTRY_DSN`` is set and the ``sentry`` extra is installed.
:func:`run_job` wraps a script's entry point: an uncaught exception is sent and
re-raised unchanged, and a non-zero exit code (returned or via ``sys.exit``)
becomes one ``error`` event. :func:`report_source_failures` sends one event for
a run in which sources failed, naming them with their status only (the error
text can echo request URLs). ``send_default_pii`` stays off.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from importlib import import_module
from types import ModuleType
from typing import Any


def init_sentry(job: str) -> ModuleType | None:
    """Initialise Sentry for one run; return the SDK, or None when it is off."""
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return None
    try:
        sdk = import_module("sentry_sdk")
    except ImportError:
        return None
    sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "local"),
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    sdk.set_tag("job", job)
    return sdk


def _exit_code(code: object) -> int:
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1  # sys.exit("message") exits 1


def run_job(job: str, main: Callable[[], object]) -> int:
    """Run ``main`` under Sentry; return its exit code (None counts as 0)."""
    sdk = init_sentry(job)
    try:
        code = _exit_code(main())
    except SystemExit as exc:
        exit_code = _exit_code(exc.code)
        if sdk is not None and exit_code != 0:
            sdk.capture_message(f"{job} exited with code {exit_code}", level="error")
            sdk.flush(timeout=5)
        raise
    except BaseException as exc:
        if sdk is not None and not isinstance(exc, KeyboardInterrupt):
            sdk.capture_exception(exc)
            sdk.flush(timeout=5)
        raise
    if sdk is not None and code != 0:
        sdk.capture_message(f"{job} exited with code {code}", level="error")
        sdk.flush(timeout=5)
    return code


def report_source_failures(
    sdk: ModuleType | None, job: str, health_records: Iterable[Mapping[str, Any]]
) -> None:
    """One event per run with failed sources: ``error`` if all failed, else ``warning``."""
    records = list(health_records)
    failed = [r for r in records if r.get("status") != "ok"]
    if sdk is None or not failed:
        return
    names = ", ".join(sorted(f"{r.get('source')} ({r.get('status')})" for r in failed))
    level = "error" if len(failed) == len(records) else "warning"
    sdk.capture_message(
        f"{job}: {len(failed)} of {len(records)} sources failed: {names}", level=level
    )
    sdk.flush(timeout=5)
