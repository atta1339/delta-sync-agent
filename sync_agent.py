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
    Scan a directory and detect new, modified, or deleted files.
    Returns a list of (relative_path, sha256_hash).
    Deleted files are represented with a hash of None.
    """
    root = Path(root)
    changed = []
    current_files = set()

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = str(path.relative_to(root))
        current_files.add(rel)

        stat = path.stat()
        mtime = stat.st_mtime
        size = stat.st_size

        prev = state.get(rel)

        # Detect new or modified files
        if prev is None or prev["mtime"] != mtime or prev["size"] != size:
            digest = file_hash(path)
            state[rel] = {
                "mtime": mtime,
                "size": size,
                "hash": digest,
            }
            changed.append((rel, digest))

    # Detect files that existed in the previous state but
    # are no longer present in the directory.
    deleted_files = set(state) - current_files

    for rel in deleted_files:
        del state[rel]
        changed.append((rel, None))

    return changed


def build_chunk_manifest(path, chunk_size=65536):
    """
    Build a chunk manifest for a file.

    Each chunk contains:
    - index
    - byte offset
    - size
    - SHA-256 hash

    The manifest also contains the file's total size and SHA-256 hash.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    chunks = []
    file_hash_object = hashlib.sha256()
    total_size = 0

    with path.open("rb") as file:
        index = 0
        offset = 0

        while True:
            data = file.read(chunk_size)

            if not data:
                break

            chunk_hash_object = hashlib.sha256(data)
            file_hash_object.update(data)

            chunks.append(
                {
                    "index": index,
                    "offset": offset,
                    "size": len(data),
                    "sha256": chunk_hash_object.hexdigest(),
                }
            )

            total_size += len(data)
            offset += len(data)
            index += 1

    return {
        "path": str(path),
        "size": total_size,
        "sha256": file_hash_object.hexdigest(),
        "chunk_size": chunk_size,
        "chunks": chunks,
    }


def verify_chunk_manifest(path, expected_manifest):
    """
    Verify that a file matches an expected chunk manifest.
    """
    if "chunk_size" not in expected_manifest:
        raise ValueError("expected_manifest must contain chunk_size")

    actual_manifest = build_chunk_manifest(
        path,
        chunk_size=expected_manifest["chunk_size"],
    )

    actual_manifest = dict(actual_manifest)
    expected_manifest = dict(expected_manifest)

    actual_manifest.pop("path", None)
    expected_manifest.pop("path", None)

    return actual_manifest == expected_manifest


def get_changed_chunks(local_manifest, remote_manifest):
    """
    Return the indexes of chunks whose SHA-256 hashes differ.
    """
    if "chunks" not in local_manifest or "chunks" not in remote_manifest:
        raise ValueError("manifests must contain chunks")

    for chunk in remote_manifest["chunks"]:
        if "index" not in chunk or "sha256" not in chunk:
            raise ValueError("each remote chunk must contain index and sha256")

    remote_chunks = {
        chunk["index"]: chunk["sha256"]
        for chunk in remote_manifest["chunks"]
    }

    changed_chunks = []

    for chunk in local_manifest["chunks"]:
        index = chunk["index"]

        if remote_chunks.get(index) != chunk["sha256"]:
            changed_chunks.append(index)

    return changed_chunks


def read_chunk(path, chunk_index, chunk_size=65536):
    """
    Read and return a specific chunk from a file.
    """
    if chunk_index < 0:
        raise ValueError("chunk_index must not be negative")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    offset = chunk_index * chunk_size

    with path.open("rb") as file:
        file.seek(offset)
        return file.read(chunk_size)


def build_changed_chunk_payload(path, changed_chunks, chunk_size=65536):
    """
    Build a payload containing only the requested chunks.
    """
    payload = []

    for chunk_index in changed_chunks:
        if chunk_index < 0:
            raise ValueError("chunk_index must not be negative")

        data = read_chunk(
            path,
            chunk_index=chunk_index,
            chunk_size=chunk_size,
        )

        payload.append(
            {
                "index": chunk_index,
                "offset": chunk_index * chunk_size,
                "data": data,
            }
        )

    return payload


def apply_chunk_payload(path, payload):
    """
    Write chunk payload data to the specified offsets in a file.
    """
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r+b") as file:
        for chunk in payload:
            offset = chunk["offset"]

            if offset < 0:
                raise ValueError("chunk offset must not be negative")

            file.seek(offset)
            file.write(chunk["data"])


def sync_file_chunks(path, remote_manifest, chunk_size=65536):
    """
    Determine changed chunks and build the payload required to synchronize them.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    local_manifest = build_chunk_manifest(
        path,
        chunk_size=chunk_size,
    )

    changed_chunks = get_changed_chunks(
        local_manifest,
        remote_manifest,
    )

    payload = build_changed_chunk_payload(
        path,
        changed_chunks,
        chunk_size=chunk_size,
    )

    return {
        "changed_chunks": changed_chunks,
        "payload": payload,
    }

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
