"""
monitor.py - watches company_data using only the Python standard library.

How it works (called "polling"):
  1. Take a "photo" of the folder: for every file remember (modified time, size, inode).
  2. Wait one second and take another photo.
  3. Compare the two photos:
        file only in new photo             -> CREATED
        file only in old photo             -> DELETED
        same file identity, different name -> RENAMED
        same name, different time/size     -> MODIFIED
  4. Send each difference to engine.record_event().

The monitor only READS file information. It never changes or deletes anything.
"""
import os
import threading
import time

import config
import engine


def scan_folder(folder):
    """Return {relative_path: {mtime, size, ino}} for every file in the folder."""
    found = {}
    for root, _dirs, files in os.walk(folder):
        for name in files:
            full = os.path.join(root, name)
            try:
                st = os.stat(full)
            except OSError:
                continue                      # file vanished while scanning
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            found[rel] = {"mtime": st.st_mtime_ns, "size": st.st_size, "ino": st.st_ino}
    return found


def _same_file(a, b):
    """Do two records describe the same underlying file (i.e. it was just renamed)?
    A pure rename keeps the size and the modified-time. We also compare the inode
    (the file's internal ID) when the OS provides one. Requiring all of them stops a
    'delete one file + create another' from being mistaken for a rename."""
    if a["size"] != b["size"] or a["mtime"] != b["mtime"]:
        return False
    if a["ino"] and b["ino"]:
        return a["ino"] == b["ino"]
    return True                               # no inode info -> size+time is our best evidence


def compare(old, new):
    """Compare two photos and return a list of (event_name, file_text)."""
    events = []
    added = set(new) - set(old)
    removed = set(old) - set(new)

    # 1. Renames = a removed name and an added name that are the same file.
    for old_name in sorted(removed):
        for new_name in sorted(added):
            if _same_file(old[old_name], new[new_name]):
                events.append(("RENAMED", f"{old_name} -> {new_name}"))
                removed.discard(old_name)
                added.discard(new_name)
                break

    # 2. What is left over is a genuine create or delete.
    for name in sorted(added):
        events.append(("CREATED", name))
    for name in sorted(removed):
        events.append(("DELETED", name))

    # 3. Same name in both photos but different time/size = modified.
    for name in sorted(set(old) & set(new)):
        if old[name]["mtime"] != new[name]["mtime"] or old[name]["size"] != new[name]["size"]:
            events.append(("MODIFIED", name))
    return events


class FolderMonitor(threading.Thread):
    """Background thread that keeps comparing photos of the folder."""

    def __init__(self, folder):
        super().__init__(daemon=True)         # daemon = stops automatically with the app
        self.folder = folder
        self.previous = scan_folder(folder)   # the first photo (no events for it)
        self._stop_flag = threading.Event()

    def run(self):
        while not self._stop_flag.is_set():
            time.sleep(config.SCAN_INTERVAL_SECONDS)
            current = scan_folder(self.folder)
            for event, file in compare(self.previous, current):
                engine.record_event(event, file, source="monitor")
            self.previous = current

    def stop(self):
        self._stop_flag.set()
