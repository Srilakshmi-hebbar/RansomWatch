"""
engine.py - the glue between events, the detector and the database.

Every file event (from the monitor OR from the simulator) goes through
record_event(). It does four things:
  1. save the event
  2. look at all events in the last WINDOW_SECONDS
  3. ask the detector to judge them
  4. save the verdict on the event and raise an alert if needed
"""
import threading
import time

import config
import database
import detector

# The monitor thread and web requests can both record events at the same time.
# The lock makes them take turns so the counts stay correct.
_lock = threading.Lock()

# Events older than this moment are ignored by the live window.
# Recover / Reset move it forward so the dashboard calms down immediately.
_ignore_before = 0.0


def acknowledge():
    global _ignore_before
    _ignore_before = time.time()


def _window_start(now):
    return max(now - config.WINDOW_SECONDS, _ignore_before)


def record_event(event, file, source="monitor"):
    with _lock:
        now = time.time()
        event_id = database.add_event(now, event, file, "NORMAL", "", source)

        window = database.get_window_events(_window_start(now))
        result = detector.analyze(window)

        database.update_event(event_id, result["level"], result["summary"])
        _maybe_raise_alert(now, result)
        return result


def log_info(event, file, reason, source="system"):
    """Store a system message (snapshot created, recovery done...). Not counted by rules."""
    with _lock:
        database.add_event(time.time(), event, file, "INFO", reason, source)


def current_evaluation():
    """Judge the last WINDOW_SECONDS right now (used by the dashboard)."""
    window = database.get_window_events(_window_start(time.time()))
    return detector.analyze(window)


def _maybe_raise_alert(now, result):
    """Raise an alert only when it is NEW or MORE SEVERE than the open one.
    This stops 48 events from creating 48 duplicate alerts."""
    if result["level"] == "NORMAL":
        return
    latest = database.get_latest_unresolved_alert()
    if latest and detector.RANK[latest["level"]] >= detector.RANK[result["level"]]:
        return
    database.add_alert(now, result["level"], result["risk_score"], result["reasons"])
