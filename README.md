# Delta Sync Agent

A Python prototype for detecting file changes and efficiently preparing
changed data for synchronisation.

The project began as a local file change-detection engine and has evolved
into a chunk-aware synchronisation prototype. It combines persistent file
metadata, SHA-256 integrity hashing, chunk manifests, changed-chunk
detection, chunk payload construction, payload application, and manifest
verification.

The implementation is intentionally modular and test-driven, providing a
foundation for future development of a reliable bandwidth-efficient file
synchronisation system.

> **Project status:** Working prototype — local change detection and
> chunk-level synchronisation engine.
>
> Remote transport, client/server communication, resumable transfers,
> authentication, encryption in transit, and production deployment are
> intentionally outside the current implementation.

---

## Overview

Delta Sync Agent explores the core mechanisms required by a
bandwidth-efficient file synchronisation utility.

The application can:

1. Recursively scan a watched directory.
2. Detect newly created, modified, and deleted files.
3. Maintain persistent local metadata.
4. Calculate SHA-256 file hashes.
5. Divide files into configurable chunks.
6. Generate per-chunk SHA-256 hashes.
7. Compare local and remote chunk manifests.
8. Identify only the chunks that differ.
9. Build a payload containing the changed chunks.
10. Apply chunk payloads at specified file offsets.
11. Verify a file against an expected chunk manifest.

The design separates these responsibilities into independently testable
functions.

---

## Current Capabilities

### File Change Detection

The change-detection layer provides:

- Recursive directory scanning
- New-file detection
- Modified-file detection
- Deleted-file detection
- File size tracking
- Modification-time tracking
- SHA-256 file hashing
- Persistent metadata storage
- Structured change reporting

Example change output:

```text
File changed: example.txt (sha256=<sha256-hash>)
