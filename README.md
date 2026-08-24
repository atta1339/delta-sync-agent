# Delta Sync Agent

A Python prototype demonstrating a bandwidth-efficient file
synchronisation engine based on file hashing, chunk manifests,
differential chunk detection, and targeted payload transfer.

The project began as a local file change-detection utility and has
evolved into a small, test-driven delta synchronisation prototype.

> **Project status:** Working prototype — local delta synchronisation
> workflow implemented and tested.
>
> The current implementation demonstrates the core mechanics of
> chunk-based synchronisation locally. Network transport, authentication,
> encryption, resumable transfers, concurrency, and distributed
> coordination remain outside the current scope.

---

## Overview

Delta Sync Agent explores the design of a reliable and
bandwidth-efficient file synchronisation system.

Instead of retransmitting an entire file when only part of it has
changed, the prototype divides files into fixed-size chunks and
calculates a SHA-256 hash for each chunk.

When comparing a local file with a remote manifest, the agent identifies
only the chunks whose hashes differ. Those chunks are then read into a
targeted payload that can be applied to the destination file.

This provides the foundation for incremental or delta-based file
synchronisation.

---

## Current Capabilities

The prototype currently implements:

### File change detection

- Recursive directory scanning
- Detection of newly discovered files
- Detection of modified files
- Detection of deleted files
- File size tracking
- Modification-time tracking
- Persistent local metadata
- SHA-256 file hashing

### Chunk-based synchronisation

- Fixed-size chunking
- Per-chunk SHA-256 hashing
- Whole-file SHA-256 hashing
- Chunk manifest generation
- Chunk manifest verification
- Local/remote chunk comparison
- Detection of changed chunks
- Detection of duplicate remote chunk indexes
- Validation of required chunk fields
- Rejection of invalid chunk indexes
- Rejection of chunk requests beyond the end of a file
- Construction of targeted chunk payloads
- Application of chunk payloads at specific file offsets

### Testing

The project includes automated tests covering:

- File change detection
- File creation and modification
- File deletion
- SHA-256 hashing
- Chunk manifest generation
- Chunk hash correctness
- Manifest verification
- Changed chunk detection
- Invalid manifest handling
- Duplicate chunk detection
- Chunk payload construction
- Chunk payload application
- Invalid chunk handling
- End-to-end chunk synchronisation

Current test suite:

```text
37 passed
