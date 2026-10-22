"""Opt-in Sentry for the legacy scraper scripts.

Off unless ``SENTRY_DSN`` is set and the ``sentry`` extra is installed.
:func:`run_job` wraps a script's entry point: an uncaught exception is sent and
re-raised unchanged, and a non-zero exit code (returned or via ``sys.exit``)
becomes one ``error`` event. :func:`report_source_failures` sends one event for
a run in which sources failed, naming them with their status only (the error
text can echo request URLs). ``send_default_pii`` stays off.

Scrubbing (security review 2026-10-22): frame locals and exception messages can
hold source bodies or tokens, so ``include_local_variables`` is off, request bodies
are never sent, and :func:`scrub_event` (``before_send``) drops frame ``vars``,
request data, breadcrumbs and extras and blanks exception messages, keeping only
the exception type. Crashes are reported as the type name plus tags.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from importlib import import_module
from types import ModuleType
from typing import Any


def _strip_frames(container: Any) -> None:
    if not isinstance(container, dict):
        return
    for item in container.get("values") or []:
        if not isinstance(item, dict):
            continue
        frames = (item.get("stacktrace") or {}).get("frames") or []
        for frame in frames:
            if isinstance(frame, dict):
                frame.pop("vars", None)


def scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """``before_send``: drop locals, request data and free text that may hold secrets."""
    for key in ("request", "breadcrumbs", "extra"):
        event.pop(key, None)
    exception = event.get("exception")
    _strip_frames(exception)
    if isinstance(exception, dict):
        for item in exception.get("values") or []:
            if isinstance(item, dict):
                item["value"] = ""
    _strip_frames(event.get("threads"))
    return event


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
        include_local_variables=False,
        max_request_body_size="never",
        before_send=scrub_event,
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
            # Type name and tags only: the message can carry tokens or source bodies.
            sdk.set_tag("exc_type", type(exc).__name__)
            sdk.capture_message(f"{job} crashed: {type(exc).__name__}", level="error")
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
