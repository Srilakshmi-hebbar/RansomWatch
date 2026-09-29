# RansomWatch — Intelligent Ransomware Activity Detection & Recovery Simulator

A safe, educational prototype that shows how abnormal file activity can be **detected, explained, protected against and recovered from**.
It is a student prototype **inspired by enterprise data-protection and cyber-resilience concepts**. It is not affiliated with, or a product of, any vendor.

> **Safety:** RansomWatch never runs real ransomware, never encrypts anything, and never deletes real files. The "attack" only edits and renames files inside a throw-away folder called `sandbox_data/`.

---

## 1. Problem statement
Ransomware attacks lock organisations out of their own data. A typical attack touches **many files in a very short time** (modify, rename, add a strange extension). Small teams often notice only after the damage is done, and may not know whether their backups are usable.

## 2. Motivation
Enterprise data-security platforms combine **early detection**, **immutable copies (snapshots)** and **fast recovery**. This project recreates those three ideas at beginner scale so the concepts can be understood, demonstrated and tested safely on a laptop.

## 3. Solution
| Capability | How RansomWatch does it |
|---|---|
| Detect | Watches `company_data/` and counts changes inside a 10-second window |
| Explain | Every alert lists the exact rule and numbers that triggered it |
| Protect | "Protect Data" copies the data into `snapshots/snapshot_YYYYMMDD_HHMMSS/` |
| Recover | "Recover" restores the sandbox from the newest snapshot and verifies it with SHA-256 |

## 4. Architecture
```
 Browser (HTML/CSS/JS)  <──JSON every 1.5 s──  Flask (app.py)
                                                   │
        ┌──────────────────────────┬───────────────┼───────────────┬────────────────┐
   monitor.py                simulator.py     snapshot.py      detector.py       database.py
 (polls company_data)     (sandbox only)   (protect/recover) (rules + risk)   (SQLite: events,
        │                       │                 │                │             alerts, snapshots)
        └────────► engine.record_event() ◄────────┘────────────────┘
```
* `engine.py` is the single entry point for events: save → look at last 10 s → judge → store verdict → maybe raise alert.
* `config.py` holds every threshold, so the detector can be tuned in one place.

**Folders**
* `company_data/` – 24 harmless dummy files, watched live, never attacked.
* `sandbox_data/` – a copy of `company_data/`; the only place the simulator writes.
* `snapshots/` – timestamped safe copies.

## 5. Technologies
Python 3, Flask, SQLite (`sqlite3`), HTML, CSS, vanilla JavaScript. File monitoring uses only the Python standard library (`os`, `threading`, `hashlib`, `shutil`). No machine learning.

## 6. Detection methodology
The detector looks at all file events in the last **10 seconds** (`WINDOW_SECONDS`).

| Rule | WARNING | CRITICAL |
|---|---|---|
| File changes (create/modify/delete/rename) | 6+ | 12+ |
| Renames | 3+ | 8+ |
| Extension changes (e.g. `.txt → .locked_sim`) | 3+ | – |

The final level is the **most severe rule that fired**. Fewer than 6 changes is **NORMAL**.

**Risk score (0–100)** = volume points (6 per change, max 60) + rename points (2 each, max 20) + extension points (4 each, max 20).
If an alert is WARNING the score is at least 31; if CRITICAL at least 61, so the score never contradicts the alert.
Bands: 0–30 LOW, 31–60 MEDIUM, 61–100 HIGH.

**Explainability example:** *"42 files changed within 10 seconds, which is abnormal compared with the normal activity threshold."* Every event row and alert stores its reason text.

## 7. Safe ransomware simulation methodology
1. Copy `company_data/` to `sandbox_data/`.
2. Phase 1: append one harmless text line to each sandbox file (MODIFIED events).
3. Phase 2: rename each file to `<name>.locked_sim` (RENAMED events).
4. Phase 3: create a harmless `SIMULATION_NOTE.txt` (CREATED event).
5. Events are recorded 50 ms apart, producing a realistic burst.

Safeguards: no encryption code exists; every write path is checked with `is_inside()` to be within `sandbox_data/`; the sandbox reset refuses to delete any folder not named `sandbox_data` inside the project.

## 8. Limitations
* Polling (1 s) can miss very short-lived files and may merge events that happen between two scans.
* Rename detection relies on inode numbers; on some file systems inodes can be reused.
* Rules are fixed thresholds; they can produce false positives (bulk legitimate edits) and cannot see slow, low-and-steady attacks.
* Snapshots are ordinary folder copies — not immutable or air-gapped like enterprise snapshots.
* The simulator imitates behaviour only; it does not model real malware, network spread or encryption.
* Single machine, no authentication, meant for local demo use.

## 9. Future improvements
* Use `watchdog` for instant file-system events.
* Add file-entropy checks to spot encrypted content.
* Adaptive baselines per folder/user, then optional ML anomaly detection.
* Immutable/read-only snapshots, retention policy and multiple restore points.
* Email/Slack alerts, user login, export of the log to CSV.
* Unit tests for the detector rules.

## 10. How to run
```bash
# 1. go into the project folder
cd ransomwatch

# 2. (recommended) create a virtual environment
python -m venv venv
#   Windows:  venv\Scripts\activate
#   Mac/Linux: source venv/bin/activate

# 3. install Flask
pip install -r requirements.txt

# 4. start the app
python app.py
```
Open **http://127.0.0.1:5000**.

**Demo order:** Protect Data → Simulate Attack → read the alert and reasons → Recover.
You can also edit or rename files inside `company_data/` by hand: the monitor will log them, and changing 6+ files quickly triggers a WARNING.
