"""
snapshot.py - "Protect Data" (make a snapshot) and "Recover" (restore from it).

Snapshot : copy company_data  ->  snapshots/snapshot_YYYYMMDD_HHMMSS/
Recovery : copy the newest snapshot  ->  sandbox_data/  (replacing the damaged copy)
           then verify every file with a SHA-256 checksum.
"""
import os
import shutil
import time

import config
import data_setup
import database
import engine


def create_snapshot():
    data_setup.ensure_sample_data()
    os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)

    name = time.strftime("snapshot_%Y%m%d_%H%M%S")
    dest = os.path.join(config.SNAPSHOT_DIR, name)
    counter = 1
    while os.path.exists(dest):               # two clicks in the same second
        counter += 1
        name = time.strftime("snapshot_%Y%m%d_%H%M%S") + f"_{counter}"
        dest = os.path.join(config.SNAPSHOT_DIR, name)

    shutil.copytree(config.COMPANY_DIR, dest)  # a plain safe copy
    count = len(data_setup.list_files(dest))

    database.add_snapshot(name, dest, count)
    engine.log_info("SNAPSHOT_CREATED", f"snapshots/{name}",
                    f"Safe copy of {count} files created.")
    return {"ok": True,
            "message": "Protected snapshot created successfully.",
            "steps": [f"Copied {count} files from company_data/ to snapshots/{name}/"]}


def recover_latest():
    snap = database.get_latest_snapshot()
    if not snap or not os.path.isdir(snap["path"]):
        return {"ok": False,
                "message": "No snapshot found. Click 'Protect Data' first, then recover."}

    steps = [f"Step 1: Found the most recent snapshot: {snap['name']} ({snap['file_count']} files)."]

    damaged = data_setup.list_files(config.SANDBOX_DIR)
    locked = [f for f in damaged if f.endswith(config.SIM_EXTENSION)]
    steps.append(f"Step 2: Sandbox currently holds {len(damaged)} files "
                 f"({len(locked)} with the fake '{config.SIM_EXTENSION}' extension).")

    data_setup.reset_sandbox(source=snap["path"])
    steps.append("Step 3: Removed the damaged sandbox_data/ folder (only the sandbox - never real data).")

    restored = data_setup.list_files(config.SANDBOX_DIR)
    steps.append(f"Step 4: Copied {len(restored)} files from the snapshot into sandbox_data/.")

    snap_files = data_setup.list_files(snap["path"])
    ok = snap_files == restored and all(
        data_setup.sha256_of(os.path.join(snap["path"], f)) ==
        data_setup.sha256_of(os.path.join(config.SANDBOX_DIR, f)) for f in snap_files)
    if not ok:
        return {"ok": False, "message": "Recovery finished but verification FAILED.", "steps": steps}
    steps.append(f"Step 5: Verified {len(restored)}/{len(snap_files)} files match the snapshot (SHA-256).")

    database.resolve_alerts()
    engine.acknowledge()          # forget the attack events in the live window
    engine.log_info("RECOVERY_COMPLETE", "sandbox_data/",
                    f"Restored {len(restored)} files from {snap['name']} and verified checksums.")
    return {"ok": True,
            "message": "Recovery complete. The simulated environment was restored safely.",
            "steps": steps}
