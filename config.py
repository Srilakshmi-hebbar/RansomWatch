"""
config.py - every setting of RansomWatch lives here.

Beginners: if you want to make the detector more or less sensitive,
this is the ONLY file you need to edit.
"""
import os

# ---------- Folder locations ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPANY_DIR = os.path.join(BASE_DIR, "company_data")    # monitored sample data (never attacked)
SANDBOX_DIR = os.path.join(BASE_DIR, "sandbox_data")    # the ONLY place the simulator touches
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")      # timestamped safe copies
DB_PATH = os.path.join(BASE_DIR, "ransomwatch.db")      # SQLite database file

# ---------- Monitoring ----------
SCAN_INTERVAL_SECONDS = 1.0      # how often the monitor looks at the folder

# ---------- Detection rules ----------
WINDOW_SECONDS = 10              # "short time window" used by every rule

WARNING_CHANGES = 6              # 6+ file changes in the window  -> WARNING
CRITICAL_CHANGES = 12            # 12+ file changes in the window -> CRITICAL

WARNING_RENAMES = 3              # 3+ renames in the window -> WARNING
CRITICAL_RENAMES = 8             # 8+ renames in the window -> CRITICAL

WARNING_EXT_CHANGES = 3          # 3+ files changing extension -> WARNING

# Extensions that ransomware families commonly add to files (used only as a hint).
SUSPICIOUS_EXTENSIONS = {
    ".locked", ".enc", ".encrypted", ".crypt", ".crypto",
    ".ransom", ".zzz", ".locked_sim",
}

# ---------- Risk score bands ----------
LOW_MAX = 30                     # 0-30  = LOW
MEDIUM_MAX = 60                  # 31-60 = MEDIUM, 61-100 = HIGH

# ---------- Simulation ----------
SIM_DELAY_SECONDS = 0.05         # pause between simulated events (makes a realistic burst)
SIM_EXTENSION = ".locked_sim"    # harmless fake extension added by the simulator
