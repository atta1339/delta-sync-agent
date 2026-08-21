# Delta Sync Agent

A Python prototype for detecting newly created and modified files within a
watched directory. The project demonstrates structured change detection,
persistent metadata tracking, SHA-256 integrity hashing, and automated testing
as the foundation of a bandwidth-efficient file synchronisation system.

> **Project status:** Working prototype — change-detection component.
>
> The current implementation focuses on local file discovery and change
> detection. Remote synchronisation, block-level delta transfer, resumable
> uploads, and bandwidth management are architectural extensions rather than
> implemented features of the current prototype.

---

## Overview

Delta Sync Agent explores the client-side foundations of a reliable file
synchronisation utility.

The prototype recursively scans a configured directory and maintains local
metadata for files that have previously been observed. A file is considered
new or modified when its recorded metadata differs from the current
filesystem state.

For detected changes, the application computes a SHA-256 hash and records the
updated metadata.

The design provides a simple foundation that can be extended toward
block-level delta synchronisation and reliable transfer over constrained or
unstable networks.

---

## Current Capabilities

The current prototype implements:

- Recursive directory scanning
- Detection of newly discovered files
- Detection of modified files
- File size tracking
- Modification-time tracking
- SHA-256 file hashing
- Persistent local metadata
- Structured change reporting
- Automated unit testing

The implementation intentionally remains small and focused so that individual
behaviours can be tested and validated independently.

---

## How It Works

The current change-detection workflow is:

```text
Watched Directory
       |
       v
Directory Scan
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
Update Local Metadata
       |
       v
Report Changed File
