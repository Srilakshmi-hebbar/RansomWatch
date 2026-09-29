"""
simulator.py - a SAFE imitation of ransomware behaviour.

What it does NOT do: it does not encrypt, delete or read anything, and it never
touches company_data or any of your real files.

What it DOES do, only inside sandbox_data/ (a throw-away copy of the sample data):
  Phase 1: append one harmless text line to every file       -> many MODIFIED events
  Phase 2: rename every file to <name>.locked_sim            -> many RENAMED events
  Phase 3: create SIMULATION_NOTE.txt                        -> one CREATED event
All of this happens within a few seconds, which is the "burst" pattern the
detector is built to catch.
"""
import os
import time

import config
import data_setup
import engine

NOTE_NAME = "SIMULATION_NOTE.txt"
MARKER = "\n[SIMULATION] Harmless line added by RansomWatch. No encryption happened.\n"


def run_simulation():
    data_setup.ensure_sample_data()
    if not data_setup.list_files(config.SANDBOX_DIR):
        data_setup.reset_sandbox()

    targets = [f for f in data_setup.list_files(config.SANDBOX_DIR)
               if not f.endswith(config.SIM_EXTENSION) and f != NOTE_NAME]
    if not targets:
        return {"ok": False,
                "message": "The sandbox is already 'attacked'. Click Recover (or Reset Demo) first."}

    engine.log_info("SIMULATION_START", "sandbox_data/",
                    f"Simulated attack started on {len(targets)} sandbox files. Real data is untouched.")

    # Phase 1: many modifications
    for name in targets:
        path = os.path.join(config.SANDBOX_DIR, name)
        _assert_safe(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(MARKER)
        engine.record_event("MODIFIED", f"sandbox_data/{name}", source="simulation")
        time.sleep(config.SIM_DELAY_SECONDS)

    # Phase 2: many renames with a fake "locked" extension
    for name in targets:
        old_path = os.path.join(config.SANDBOX_DIR, name)
        new_name = name + config.SIM_EXTENSION
        new_path = os.path.join(config.SANDBOX_DIR, new_name)
        _assert_safe(old_path)
        _assert_safe(new_path)
        os.rename(old_path, new_path)
        engine.record_event("RENAMED", f"sandbox_data/{name} -> sandbox_data/{new_name}",
                            source="simulation")
        time.sleep(config.SIM_DELAY_SECONDS)

    # Phase 3: a fake "ransom note" (plain harmless text)
    note_path = os.path.join(config.SANDBOX_DIR, NOTE_NAME)
    _assert_safe(note_path)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("This is a SIMULATION note. Nothing was encrypted. Click Recover.\n")
    engine.record_event("CREATED", f"sandbox_data/{NOTE_NAME}", source="simulation")

    result = engine.current_evaluation()
    return {
        "ok": True,
        "message": (f"Simulation finished: {len(targets)} files modified and {len(targets)} renamed "
                    f"inside sandbox_data. Detection result: {result['level']}."),
        "level": result["level"],
        "reasons": result["reasons"],
    }


def _assert_safe(path):
    """Last line of defence: never operate outside sandbox_data."""
    if not data_setup.is_inside(path, config.SANDBOX_DIR):
        raise RuntimeError(f"SAFETY STOP: {path} is outside the sandbox.")
