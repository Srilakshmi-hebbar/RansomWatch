"""
detector.py - the explainable, rule-based detection engine.

It receives the list of file events from the last WINDOW_SECONDS seconds and
answers three questions:
  1. Is this NORMAL, WARNING or CRITICAL?
  2. What is the risk score (0-100)?
  3. WHY?  (a list of plain-English reasons)

No machine learning - just counting and comparing with thresholds.
That is what makes every decision easy to explain.
"""
import os

import config

# Used to compare severities: a bigger number is more severe.
RANK = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}


def split_rename(text):
    """A rename event is stored as 'old -> new'. Return (old, new)."""
    if " -> " in text:
        old, new = text.split(" -> ", 1)
        return old, new
    return text, text


def risk_level(score):
    """Turn a 0-100 score into LOW / MEDIUM / HIGH."""
    if score <= config.LOW_MAX:
        return "LOW"
    if score <= config.MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def analyze(events):
    w = config.WINDOW_SECONDS

    # ---------- Step 1: count things ----------
    total = len(events)
    modifications = sum(1 for e in events if e["event"] == "MODIFIED")
    renames = [e for e in events if e["event"] == "RENAMED"]

    ext_changes = 0          # renames where the file extension changed (.txt -> .locked_sim)
    suspicious_ext = 0       # ...and the new extension is on our suspicious list
    for e in renames:
        old, new = split_rename(e["file"])
        old_ext = os.path.splitext(old)[1].lower()
        new_ext = os.path.splitext(new)[1].lower()
        if old_ext != new_ext:
            ext_changes += 1
            if new_ext in config.SUSPICIOUS_EXTENSIONS:
                suspicious_ext += 1

    # ---------- Step 2: apply the rules ----------
    findings = []            # list of (level, explanation)

    # Rule 1 - volume of changes
    if total >= config.CRITICAL_CHANGES:
        findings.append(("CRITICAL",
            f"{total} files changed within {w} seconds, which is abnormal compared with "
            f"the normal activity threshold (critical at {config.CRITICAL_CHANGES}+ changes)."))
    elif total >= config.WARNING_CHANGES:
        findings.append(("WARNING",
            f"{total} files changed within {w} seconds, above the normal limit of "
            f"{config.WARNING_CHANGES - 1} changes (warning at {config.WARNING_CHANGES}+)."))

    # Rule 2 - burst of renames
    if len(renames) >= config.CRITICAL_RENAMES:
        findings.append(("CRITICAL",
            f"{len(renames)} files were renamed within {w} seconds - mass renaming is a "
            f"classic ransomware behaviour (critical at {config.CRITICAL_RENAMES}+ renames)."))
    elif len(renames) >= config.WARNING_RENAMES:
        findings.append(("WARNING",
            f"{len(renames)} files were renamed within {w} seconds "
            f"(warning at {config.WARNING_RENAMES}+ renames)."))

    # Rule 3 - extension changes
    if ext_changes >= config.WARNING_EXT_CHANGES:
        findings.append(("WARNING",
            f"{ext_changes} files changed their file extension within {w} seconds "
            f"({suspicious_ext} of them to a known suspicious extension such as "
            f"{config.SIM_EXTENSION})."))

    # ---------- Step 3: final level = the most severe finding ----------
    level = "NORMAL"
    for lvl, _ in findings:
        if RANK[lvl] > RANK[level]:
            level = lvl

    if findings:
        reasons = [text for _, text in findings]
    else:
        reasons = [f"Only {total} file change(s) in the last {w} seconds - within the "
                   f"normal threshold (warning starts at {config.WARNING_CHANGES})."]

    # ---------- Step 4: risk score (0-100) ----------
    #   volume points    : 6 per change, max 60
    #   rename points    : 2 per rename, max 20
    #   extension points : 4 per extension change, max 20
    volume_pts = min(60, total * 6)
    rename_pts = min(20, len(renames) * 2)
    ext_pts = min(20, ext_changes * 4)
    score = min(100, volume_pts + rename_pts + ext_pts)

    # Safety floor so the score never contradicts the alert level.
    floor = {"NORMAL": 0, "WARNING": config.LOW_MAX + 1, "CRITICAL": config.MEDIUM_MAX + 1}[level]
    floor_applied = score < floor
    score = max(score, floor)

    return {
        "level": level,
        "reasons": reasons,
        "summary": " | ".join(reasons),
        "total_changes": total,
        "modifications": modifications,
        "renames": len(renames),
        "ext_changes": ext_changes,
        "suspicious_ext": suspicious_ext,
        "risk_score": score,
        "risk_level": risk_level(score),
        "breakdown": {"volume": volume_pts, "renames": rename_pts,
                      "extensions": ext_pts, "floor_applied": floor_applied},
    }
