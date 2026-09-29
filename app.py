"""
app.py - the Flask web server. Run this file to start RansomWatch.

Routes:
  GET  /               -> the dashboard page
  GET  /api/status     -> JSON with everything the dashboard shows
  POST /api/simulate   -> "Simulate Attack" button
  POST /api/protect    -> "Protect Data" button
  POST /api/recover    -> "Recover" button
  POST /api/reset      -> "Reset Demo" button
"""
import os
import time

from flask import Flask, jsonify, render_template

import config
import data_setup
import database
import detector
import engine
import monitor
import simulator
import snapshot

app = Flask(__name__)


def sandbox_state():
    files = data_setup.list_files(config.SANDBOX_DIR)
    locked = sum(1 for f in files if f.endswith(config.SIM_EXTENSION))
    return {"files": len(files), "locked": locked,
            "state": "COMPROMISED" if locked else "CLEAN"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    now = time.time()
    live = engine.current_evaluation()                     # last 10 seconds
    incident = database.get_latest_unresolved_alert()      # open alert (stays until Recover)

    # Overall status = the more severe of "right now" and "open incident".
    level = live["level"]
    if incident and detector.RANK[incident["level"]] > detector.RANK[level]:
        level = incident["level"]

    score = max(live["risk_score"], incident["risk_score"] if incident else 0)

    # Explanation: prefer the live reasons; otherwise show the open alert's reasons.
    if live["level"] != "NORMAL" or not incident:
        reasons = live["reasons"]
    else:
        reasons = incident["reasons"]

    # Tiny chart: number of events in each 5-second bucket for the last 60 seconds.
    buckets = [0] * 12
    for e in database.get_window_events(now - 60):
        idx = int((now - e["ts"]) // 5)
        if 0 <= idx < 12:
            buckets[11 - idx] += 1

    modified_recent = {e["file"] for e in database.get_window_events(now - 60)
                       if e["event"] == "MODIFIED"}

    latest_snap = database.get_latest_snapshot()
    return jsonify({
        "total_files": len(monitor.scan_folder(config.COMPANY_DIR)),
        "modified_recent": len(modified_recent),
        "status": level,
        "incident_active": incident is not None,
        "warnings": database.count_alerts("WARNING"),
        "criticals": database.count_alerts("CRITICAL"),
        "risk_score": score,
        "risk_level": detector.risk_level(score),
        "reasons": reasons,
        "live": live,
        "chart": buckets,
        "events": database.get_recent_events(50),
        "alerts": database.get_alerts(6),
        "snapshot": latest_snap,
        "snapshot_count": database.count_snapshots(),
        "sandbox": sandbox_state(),
        "rules": {
            "window": config.WINDOW_SECONDS,
            "warning_changes": config.WARNING_CHANGES,
            "critical_changes": config.CRITICAL_CHANGES,
            "warning_renames": config.WARNING_RENAMES,
            "critical_renames": config.CRITICAL_RENAMES,
            "warning_ext": config.WARNING_EXT_CHANGES,
        },
    })


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    return jsonify(simulator.run_simulation())


@app.route("/api/protect", methods=["POST"])
def api_protect():
    return jsonify(snapshot.create_snapshot())


@app.route("/api/recover", methods=["POST"])
def api_recover():
    return jsonify(snapshot.recover_latest())


@app.route("/api/reset", methods=["POST"])
def api_reset():
    database.clear_activity()
    engine.acknowledge()
    data_setup.reset_sandbox()
    return jsonify({"ok": True, "message": "Demo reset: log cleared and sandbox restored."})


def prepare():
    """Create folders, database and sample data (safe to call many times)."""
    database.init_db()
    data_setup.ensure_sample_data()
    os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)
    if not data_setup.list_files(config.SANDBOX_DIR):
        data_setup.reset_sandbox()


if __name__ == "__main__":
    prepare()
    monitor.FolderMonitor(config.COMPANY_DIR).start()      # start watching in the background
    print("RansomWatch running at http://127.0.0.1:5000")
    # debug=False on purpose: Flask's auto-reloader would start the monitor twice.
    app.run(host="127.0.0.1", port=5000, debug=False)
