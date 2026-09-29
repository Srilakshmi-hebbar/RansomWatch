"""
database.py - all SQLite code lives here.

Three tables:
  events     -> every file event (CREATED / MODIFIED / DELETED / RENAMED) + system messages
  alerts     -> raised when the detector decides something is WARNING or CRITICAL
  snapshots  -> list of protected snapshot folders we created
"""
import json
import sqlite3
import time

import config

# The event types that count towards the detection rules.
# (System messages like SNAPSHOT_CREATED are stored too, but never counted.)
FILE_EVENTS = ("CREATED", "MODIFIED", "DELETED", "RENAMED")


def get_conn():
    """Open a new connection. We open one per operation so threads never share one."""
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row          # lets us read columns by name
    return conn


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE and return the new row id."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def query(sql, params=()):
    """Run a SELECT and return a list of dictionaries."""
    conn = get_conn()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _time_text(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL NOT NULL,              -- epoch seconds (used for maths)
            time_text TEXT NOT NULL,              -- human readable time
            event     TEXT NOT NULL,
            file      TEXT NOT NULL,
            severity  TEXT NOT NULL DEFAULT 'NORMAL',
            reason    TEXT NOT NULL DEFAULT '',
            source    TEXT NOT NULL DEFAULT 'monitor'
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         REAL NOT NULL,
            time_text  TEXT NOT NULL,
            level      TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            reasons    TEXT NOT NULL,             -- JSON list of strings
            resolved   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS snapshots (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            path       TEXT NOT NULL,
            ts         REAL NOT NULL,
            time_text  TEXT NOT NULL,
            file_count INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ---------------- events ----------------
def add_event(ts, event, file, severity="NORMAL", reason="", source="monitor"):
    return execute(
        "INSERT INTO events (ts, time_text, event, file, severity, reason, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, _time_text(ts), event, file, severity, reason, source),
    )


def update_event(event_id, severity, reason):
    execute("UPDATE events SET severity = ?, reason = ? WHERE id = ?",
            (severity, reason, event_id))


def get_recent_events(limit=50):
    return query("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))


def get_window_events(since_ts):
    """File events that happened after `since_ts` (used by the detector)."""
    marks = ",".join("?" * len(FILE_EVENTS))
    return query(
        f"SELECT * FROM events WHERE ts >= ? AND event IN ({marks}) ORDER BY ts",
        (since_ts, *FILE_EVENTS),
    )


# ---------------- alerts ----------------
def add_alert(ts, level, risk_score, reasons):
    return execute(
        "INSERT INTO alerts (ts, time_text, level, risk_score, reasons) VALUES (?, ?, ?, ?, ?)",
        (ts, _time_text(ts), level, risk_score, json.dumps(reasons)),
    )


def _parse_alert(row):
    row["reasons"] = json.loads(row["reasons"])
    return row


def get_alerts(limit=8):
    return [_parse_alert(r) for r in
            query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))]


def get_latest_unresolved_alert():
    rows = query("SELECT * FROM alerts WHERE resolved = 0 ORDER BY id DESC LIMIT 1")
    return _parse_alert(rows[0]) if rows else None


def count_alerts(level):
    return query("SELECT COUNT(*) AS n FROM alerts WHERE level = ?", (level,))[0]["n"]


def resolve_alerts():
    execute("UPDATE alerts SET resolved = 1 WHERE resolved = 0")


# ---------------- snapshots ----------------
def add_snapshot(name, path, file_count):
    ts = time.time()
    return execute(
        "INSERT INTO snapshots (name, path, ts, time_text, file_count) VALUES (?, ?, ?, ?, ?)",
        (name, path, ts, _time_text(ts), file_count),
    )


def get_latest_snapshot():
    rows = query("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
    return rows[0] if rows else None


def count_snapshots():
    return query("SELECT COUNT(*) AS n FROM snapshots")[0]["n"]


# ---------------- reset ----------------
def clear_activity():
    """Used by 'Reset Demo': forget events and alerts (snapshots are kept)."""
    execute("DELETE FROM events")
    execute("DELETE FROM alerts")
