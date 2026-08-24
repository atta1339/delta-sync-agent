# Delta Sync Agent

A Python prototype for efficient file synchronisation using metadata-based
change detection, SHA-256 integrity hashing, and chunk-level delta transfer.

The project explores the engineering foundations of a synchronisation system
designed to minimise unnecessary data transfer by identifying changed files
and, where appropriate, transferring only the affected file chunks.

> **Project status:** Working prototype — local change detection and
> chunk-level synchronisation foundation implemented.

---

## Overview

Delta Sync Agent is a Python-based prototype exploring the core mechanisms
behind an efficient file synchronisation utility.

The project began as a metadata-based change detection engine and has been
extended with chunk-level processing. It can now:

1. Detect newly created, modified, and deleted files.
2. Maintain persistent local file metadata.
3. Calculate whole-file SHA-256 hashes.
4. Divide files into deterministic chunks.
5. Generate manifests containing per-chunk metadata and SHA-256 hashes.
6. Compare local and remote-style manifests.
7. Identify only the chunks whose content differs.
8. Build a payload containing the changed chunks.
9. Apply chunk payloads at their corresponding file offsets.
10. Verify a file against an expected chunk manifest.

The implementation is intentionally modular so that each component can be
tested independently before being incorporated into a more complete
synchronisation workflow.

---

## Current Architecture

The current implementation consists of two closely related layers.

### 1. File Change Detection

The original change-detection layer monitors a configured directory and
maintains persistent metadata for observed files.

```text
Watched Directory
       |
       v
Recursive Directory Scan
       |
       v
Read File Metadata
       |
       v
Compare With Previous State
       |
       +------ No Change ------> Continue
       |
       v
Compute SHA-256
       |
       v
Update Metadata
       |
       v
Report Change
```
