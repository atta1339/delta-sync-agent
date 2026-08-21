"""
delta-sync-agent
Author: Attaollah Kouhzad

Prototype demonstrating a simple change detection engine for a
directory synchronisation utility. Tracks file metadata, computes
SHA-256 hashes, and identifies newly created or modified files.
"""

import os
import json
import hashlib
from pathlib import Path

METADATA_FILE = "metadata.json"


# ---------------------------------------------------------
# Metadata handling
# ---------------------------------------------------------
def load_state():
    """Load metadata from disk."""
    if not os.path.exists(METADATA_FILE):
        return {}
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    """Persist metadata to disk."""
    with open(METADATA_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------
# Hashing
# ---------------------------------------------------------
def file_hash(path, block_size=65536):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


# ---------------------------------------------------------
# Change detection
# ---------------------------------------------------------
def scan_directory(root, state):
    """
    Scan a directory and detect new or modified files.
    Returns a list of (relative_path, sha256_hash).
    """
    root = Path(root)
    changed = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = str(path.relative_to(root))
        stat = path.stat()
        mtime = stat.st_mtime
        size = stat.st_size

        prev = state.get(rel)

        # Detect new or modified files
        if prev is None or prev["mtime"] != mtime or prev["size"] != size:
            digest = file_hash(path)
            state[rel] = {"mtime": mtime, "size": size, "hash": digest}
            changed.append((rel, digest))

    return changed



# ---------------------------------------------------------
# Main execution
# ---------------------------------------------------------
if __name__ == "__main__":
    watched_dir = "watched_dir"

    state = load_state()
    changed_files = scan_directory(watched_dir, state)
    save_state(state)

    for rel, digest in changed_files:
        print(f"File changed: {rel} (sha256={digest})")

