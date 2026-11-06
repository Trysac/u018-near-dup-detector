# Project record

## Objective

Detect near-duplicate documents with process-stable MinHash and LSH banding plus 64-bit SimHash, verified candidate pairs and deterministic clusters. Libraries that use Python's built-in hash give different results per process; this one never does.

## Scope

- In scope: the public API documented in [README.md](../README.md): shingling, seeded MinHash, LSH banding index, SimHash, and `find_duplicates` with verification and union-find clustering. Typed and tested.
- Out of scope: persistence, streaming at scale, embedding-based semantic duplicates, language detection, and anything that needs runtime dependencies or I/O without an accepted ADR.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | pending measurement |
| Hours (human) | pending measurement |
| Cost (USD) | pending measurement |
