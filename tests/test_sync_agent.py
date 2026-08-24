import json
from pathlib import Path

import sync_agent


def test_new_file_is_detected(tmp_path, monkeypatch):
    """A file absent from the previous state is detected."""
    watched = tmp_path / "watched"
    watched.mkdir()

    test_file = watched / "example.txt"
    test_file.write_text("hello")

    monkeypatch.chdir(tmp_path)

    state = {}
    changed = sync_agent.scan_directory(watched, state)

    assert len(changed) == 1
    assert changed[0][0] == "example.txt"
    assert changed[0][1] == sync_agent.file_hash(test_file)


def test_unchanged_file_is_not_detected(tmp_path, monkeypatch):
    """A file with unchanged metadata is not processed again."""
    watched = tmp_path / "watched"
    watched.mkdir()

    test_file = watched / "example.txt"
    test_file.write_text("hello")

    monkeypatch.chdir(tmp_path)

    state = {}

    first_scan = sync_agent.scan_directory(watched, state)
    assert len(first_scan) == 1

    second_scan = sync_agent.scan_directory(watched, state)

    assert second_scan == []


def test_modified_file_is_detected(tmp_path, monkeypatch):
    """Changing file content results in a new detection."""
    watched = tmp_path / "watched"
    watched.mkdir()

    test_file = watched / "example.txt"
    test_file.write_text("hello")

    monkeypatch.chdir(tmp_path)

    state = {}

    first_scan = sync_agent.scan_directory(watched, state)
    first_hash = first_scan[0][1]

    test_file.write_text("hello world")

    second_scan = sync_agent.scan_directory(watched, state)

    assert len(second_scan) == 1
    assert second_scan[0][0] == "example.txt"
    assert second_scan[0][1] != first_hash


def test_hash_changes_when_content_changes(tmp_path):
    """SHA-256 output changes when file content changes."""
    test_file = tmp_path / "example.txt"

    test_file.write_text("before")
    first_hash = sync_agent.file_hash(test_file)

    test_file.write_text("after")
    second_hash = sync_agent.file_hash(test_file)

    assert first_hash != second_hash


def test_metadata_only_change_does_not_change_content_hash(
    tmp_path, monkeypatch
):
    """A metadata change alone does not alter the content hash."""
    watched = tmp_path / "watched"
    watched.mkdir()

    test_file = watched / "example.txt"
    test_file.write_text("same content")

    monkeypatch.chdir(tmp_path)

    state = {}

    first_scan = sync_agent.scan_directory(watched, state)
    first_hash = first_scan[0][1]

    # Change the modification time without changing file content.
    original_stat = test_file.stat()
    new_mtime = original_stat.st_mtime + 10

    import os

    os.utime(test_file, (new_mtime, new_mtime))

    second_scan = sync_agent.scan_directory(watched, state)

    assert len(second_scan) == 1
    assert second_scan[0][1] == first_hash


def test_nested_files_are_detected(tmp_path, monkeypatch):
    """Files in nested directories are discovered recursively."""
    watched = tmp_path / "watched"
    nested = watched / "documents" / "reports"
    nested.mkdir(parents=True)

    test_file = nested / "report.txt"
    test_file.write_text("report")

    monkeypatch.chdir(tmp_path)

    state = {}
    changed = sync_agent.scan_directory(watched, state)

    assert len(changed) == 1
    assert changed[0][0] == str(
        Path("documents") / "reports" / "report.txt"
    )


def test_metadata_persists_between_load_and_save(
    tmp_path, monkeypatch
):
    """Stored metadata can be written and loaded again."""
    monkeypatch.chdir(tmp_path)

    state = {
        "example.txt": {
            "mtime": 123.0,
            "size": 5,
            "hash": "abc123",
        }
    }

    sync_agent.save_state(state)

    loaded = sync_agent.load_state()

    assert loaded == state


def test_large_file_is_hashed_incrementally(tmp_path):
    """A larger file can be hashed using the configured block size."""
    test_file = tmp_path / "large.bin"

    test_file.write_bytes(b"A" * (1024 * 1024))

    digest = sync_agent.file_hash(
        test_file,
        block_size=4096,
    )

    assert isinstance(digest, str)
    assert len(digest) == 64
def test_deleted_file_is_detected(tmp_path, monkeypatch):
    """A file removed from the directory is detected as deleted."""
    watched = tmp_path / "watched"
    watched.mkdir()

    test_file = watched / "example.txt"
    test_file.write_text("hello")

    monkeypatch.chdir(tmp_path)

    state = {}

    first_scan = sync_agent.scan_directory(watched, state)
    assert len(first_scan) == 1

    test_file.unlink()

    second_scan = sync_agent.scan_directory(watched, state)

    assert second_scan == [("example.txt", None)]
    assert "example.txt" not in state


def test_multiple_deleted_files_are_detected(tmp_path, monkeypatch):
    """Multiple files removed from the directory are detected."""
    watched = tmp_path / "watched"
    watched.mkdir()

    first_file = watched / "first.txt"
    second_file = watched / "second.txt"

    first_file.write_text("first")
    second_file.write_text("second")

    monkeypatch.chdir(tmp_path)

    state = {}

    first_scan = sync_agent.scan_directory(watched, state)
    assert len(first_scan) == 2

    first_file.unlink()
    second_file.unlink()

    second_scan = sync_agent.scan_directory(watched, state)

    assert set(second_scan) == {
        ("first.txt", None),
        ("second.txt", None),
    }
    assert state == {}


def test_build_chunk_manifest(tmp_path):
    from sync_agent import build_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = build_chunk_manifest(file_path, chunk_size=4)

    assert manifest["path"] == str(file_path)
    assert manifest["size"] == 10
    assert manifest["chunk_size"] == 4
    assert len(manifest["chunks"]) == 3

    assert manifest["chunks"][0]["index"] == 0
    assert manifest["chunks"][0]["offset"] == 0
    assert manifest["chunks"][0]["size"] == 4

    assert manifest["chunks"][1]["index"] == 1
    assert manifest["chunks"][1]["offset"] == 4
    assert manifest["chunks"][1]["size"] == 4

    assert manifest["chunks"][2]["index"] == 2
    assert manifest["chunks"][2]["offset"] == 8
    assert manifest["chunks"][2]["size"] == 2


def test_build_chunk_manifest_hashes_are_correct(tmp_path):
    import hashlib

    from sync_agent import build_chunk_manifest

    file_path = tmp_path / "sample.bin"
    content = b"abcdefghij"
    file_path.write_bytes(content)

    manifest = build_chunk_manifest(file_path, chunk_size=4)

    assert manifest["sha256"] == hashlib.sha256(content).hexdigest()

    for chunk in manifest["chunks"]:
        start = chunk["offset"]
        end = start + chunk["size"]
        expected_hash = hashlib.sha256(content[start:end]).hexdigest()

        assert chunk["sha256"] == expected_hash


def test_build_chunk_manifest_rejects_invalid_chunk_size(tmp_path):
    import pytest

    from sync_agent import build_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"test")

    with pytest.raises(ValueError):
        build_chunk_manifest(file_path, chunk_size=0)

    with pytest.raises(ValueError):
        build_chunk_manifest(file_path, chunk_size=-1)


def test_build_chunk_manifest_rejects_missing_file(tmp_path):
    import pytest

    from sync_agent import build_chunk_manifest

    missing_file = tmp_path / "missing.bin"

    with pytest.raises(FileNotFoundError):
        build_chunk_manifest(missing_file)


def test_get_changed_chunks_returns_empty_for_identical_manifests():
    from sync_agent import get_changed_chunks

    manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 1, "offset": 4, "size": 4, "sha256": "bbb"},
        ]
    }

    assert get_changed_chunks(manifest, manifest) == []


def test_get_changed_chunks_detects_changed_chunk():
    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 1, "offset": 4, "size": 4, "sha256": "changed"},
            {"index": 2, "offset": 8, "size": 2, "sha256": "ccc"},
        ]
    }

    remote_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 1, "offset": 4, "size": 4, "sha256": "bbb"},
            {"index": 2, "offset": 8, "size": 2, "sha256": "ccc"},
        ]
    }

    assert get_changed_chunks(local_manifest, remote_manifest) == [1]


def test_get_changed_chunks_detects_new_local_chunk():
    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 1, "offset": 4, "size": 4, "sha256": "bbb"},
            {"index": 2, "offset": 8, "size": 2, "sha256": "ccc"},
        ]
    }

    remote_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 1, "offset": 4, "size": 4, "sha256": "bbb"},
        ]
    }

    assert get_changed_chunks(local_manifest, remote_manifest) == [2]


def test_read_chunk_returns_requested_chunk(tmp_path):
    from sync_agent import read_chunk

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    assert read_chunk(file_path, chunk_index=0, chunk_size=4) == b"abcd"
    assert read_chunk(file_path, chunk_index=1, chunk_size=4) == b"efgh"
    assert read_chunk(file_path, chunk_index=2, chunk_size=4) == b"ij"


def test_read_chunk_rejects_invalid_chunk_index(tmp_path):
    import pytest

    from sync_agent import read_chunk

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    with pytest.raises(ValueError):
        read_chunk(file_path, chunk_index=-1, chunk_size=4)

def test_build_changed_chunk_payload_returns_requested_chunks(tmp_path):
    from sync_agent import build_changed_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    payload = build_changed_chunk_payload(
        file_path,
        changed_chunks=[0, 2],
        chunk_size=4,
    )

    assert len(payload) == 2

    assert payload[0]["index"] == 0
    assert payload[0]["offset"] == 0
    assert payload[0]["data"] == b"abcd"

    assert payload[1]["index"] == 2
    assert payload[1]["offset"] == 8
    assert payload[1]["data"] == b"ij"


def test_build_changed_chunk_payload_rejects_invalid_chunk_index(tmp_path):
    import pytest

    from sync_agent import build_changed_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    with pytest.raises(ValueError):
        build_changed_chunk_payload(
            file_path,
            changed_chunks=[-1],
            chunk_size=4,
        )
def test_apply_chunk_payload_writes_chunks_at_correct_offsets(tmp_path):
    from sync_agent import apply_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    payload = [
        {
            "index": 0,
            "offset": 0,
            "data": b"ABCD",
        },
        {
            "index": 2,
            "offset": 8,
            "data": b"XY",
        },
    ]

    apply_chunk_payload(file_path, payload)

    assert file_path.read_bytes() == b"ABCD" + b"efgh" + b"XY"
def test_apply_chunk_payload_rejects_negative_offset(tmp_path):
    import pytest

    from sync_agent import apply_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    payload = [
        {
            "index": 0,
            "offset": -1,
            "data": b"ABCD",
        }
    ]

    with pytest.raises(ValueError):
        apply_chunk_payload(file_path, payload)


def test_sync_file_chunks_returns_empty_for_identical_file(tmp_path):
    import hashlib

    from sync_agent import sync_file_chunks

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    remote_manifest = {
        "path": str(file_path),
        "size": 10,
        "sha256": hashlib.sha256(b"abcdefghij").hexdigest(),
        "chunk_size": 4,
        "chunks": [
            {
                "index": 0,
                "offset": 0,
                "size": 4,
                "sha256": hashlib.sha256(b"abcd").hexdigest(),
            },
            {
                "index": 1,
                "offset": 4,
                "size": 4,
                "sha256": hashlib.sha256(b"efgh").hexdigest(),
            },
            {
                "index": 2,
                "offset": 8,
                "size": 2,
                "sha256": hashlib.sha256(b"ij").hexdigest(),
            },
        ],
    }

    result = sync_file_chunks(
        file_path,
        remote_manifest,
        chunk_size=4,
    )

    assert result["changed_chunks"] == []
    assert result["payload"] == []


def test_sync_file_chunks_returns_only_changed_chunks(tmp_path):
    import hashlib

    from sync_agent import sync_file_chunks

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    unchanged_chunk_hash = hashlib.sha256(b"efgh").hexdigest()

    remote_manifest = {
        "path": str(file_path),
        "size": 10,
        "sha256": "remote-placeholder",
        "chunk_size": 4,
        "chunks": [
            {
                "index": 0,
                "offset": 0,
                "size": 4,
                "sha256": "old-hash-0",
            },
            {
                "index": 1,
                "offset": 4,
                "size": 4,
                "sha256": unchanged_chunk_hash,
            },
            {
                "index": 2,
                "offset": 8,
                "size": 2,
                "sha256": "old-hash-2",
            },
        ],
    }

    result = sync_file_chunks(
        file_path,
        remote_manifest,
        chunk_size=4,
    )

    assert result["changed_chunks"] == [0, 2]
    assert len(result["payload"]) == 2

    assert result["payload"][0]["index"] == 0
    assert result["payload"][0]["data"] == b"abcd"

    assert result["payload"][1]["index"] == 2
    assert result["payload"][1]["data"] == b"ij"


def test_sync_file_chunks_rejects_invalid_chunk_size(tmp_path):
    import pytest

    from sync_agent import sync_file_chunks

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    remote_manifest = {
        "chunks": [],
    }

    with pytest.raises(ValueError):
        sync_file_chunks(
            file_path,
            remote_manifest,
            chunk_size=0,
        )


def test_verify_chunk_manifest_accepts_matching_file(tmp_path):
    from sync_agent import build_chunk_manifest, verify_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = build_chunk_manifest(file_path, chunk_size=4)

    assert verify_chunk_manifest(file_path, manifest) is True


def test_verify_chunk_manifest_rejects_modified_file(tmp_path):
    from sync_agent import build_chunk_manifest, verify_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = build_chunk_manifest(file_path, chunk_size=4)

    file_path.write_bytes(b"abcdZZghij")

    assert verify_chunk_manifest(file_path, manifest) is False


def test_verify_chunk_manifest_ignores_manifest_path(tmp_path):
    from sync_agent import build_chunk_manifest, verify_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = build_chunk_manifest(file_path, chunk_size=4)
    manifest["path"] = "remote/path/sample.bin"

    assert verify_chunk_manifest(file_path, manifest) is True


def test_verify_chunk_manifest_rejects_manifest_without_chunk_size(tmp_path):
    import pytest

    from sync_agent import verify_chunk_manifest

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = {
        "size": 10,
        "sha256": "placeholder",
        "chunks": [],
    }

    with pytest.raises(ValueError):
        verify_chunk_manifest(file_path, manifest)


def test_get_changed_chunks_detects_remote_hash_mismatch():
    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "local-hash"},
        ]
    }

    remote_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "remote-hash"},
        ]
    }

    assert get_changed_chunks(local_manifest, remote_manifest) == [0]


def test_get_changed_chunks_rejects_manifest_without_chunks():
    import pytest

    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
        ]
    }

    remote_manifest = {}

    with pytest.raises(ValueError):
        get_changed_chunks(local_manifest, remote_manifest)


def test_get_changed_chunks_rejects_chunk_without_index():
    import pytest

    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
        ]
    }

    remote_manifest = {
        "chunks": [
            {"offset": 0, "size": 4, "sha256": "aaa"},
        ]
    }

    with pytest.raises(ValueError):
        get_changed_chunks(local_manifest, remote_manifest)


def test_get_changed_chunks_rejects_duplicate_remote_chunk_indexes():
    import pytest

    from sync_agent import get_changed_chunks

    local_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
        ]
    }

    remote_manifest = {
        "chunks": [
            {"index": 0, "offset": 0, "size": 4, "sha256": "aaa"},
            {"index": 0, "offset": 0, "size": 4, "sha256": "bbb"},
        ]
    }

    with pytest.raises(ValueError):
        get_changed_chunks(local_manifest, remote_manifest)


def test_build_changed_chunk_payload_preserves_chunk_metadata(tmp_path):
    import hashlib

    from sync_agent import build_changed_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    manifest = {
        "chunks": [
            {
                "index": 2,
                "offset": 8,
                "size": 2,
                "sha256": hashlib.sha256(b"ij").hexdigest(),
            },
        ]
    }

    payload = build_changed_chunk_payload(
        file_path,
        changed_chunks=[2],
        chunk_size=4,
    )

    assert payload == [
        {
            "index": 2,
            "offset": 8,
            "data": b"ij",
        }
    ]


def test_build_changed_chunk_payload_rejects_chunk_beyond_end_of_file(tmp_path):
    import pytest

    from sync_agent import build_changed_chunk_payload

    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"abcdefghij")

    with pytest.raises(ValueError):
        build_changed_chunk_payload(
            file_path,
            changed_chunks=[3],
            chunk_size=4,
        )
def test_end_to_end_chunk_sync_updates_destination(tmp_path):
    from sync_agent import (
        apply_chunk_payload,
        build_chunk_manifest,
        sync_file_chunks,
        verify_chunk_manifest,
    )

    source_path = tmp_path / "source.bin"
    destination_path = tmp_path / "destination.bin"

    source_path.write_bytes(b"abcdefghij")
    destination_path.write_bytes(b"abcdXXXXij")

    remote_manifest = build_chunk_manifest(
        destination_path,
        chunk_size=4,
    )

    result = sync_file_chunks(
        source_path,
        remote_manifest,
        chunk_size=4,
    )

    assert result["changed_chunks"] == [1]

    apply_chunk_payload(
        destination_path,
        result["payload"],
    )

    source_manifest = build_chunk_manifest(
        source_path,
        chunk_size=4,
    )

    assert verify_chunk_manifest(
        destination_path,
        source_manifest,
    )