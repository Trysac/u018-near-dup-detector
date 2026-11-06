# Architecture

## Purpose

`trysac-near-dup-detector` is a small, dependency-free Python library that detects near-duplicate documents with process-stable MinHash and LSH banding plus 64-bit SimHash, verified candidate pairs and deterministic clusters.

## Shape

```text
caller code --> near_dup_detector (public API in __init__.py)
                    |
                    +-- pure functions and classes, no I/O, no global state
```

- **Modules**: `shingling.py` (normalization, shingles), `_hashing.py` (BLAKE2b 64-bit hash), `minhash.py` (MinHasher), `lsh.py` (LSHIndex), `fingerprint.py` (simhash), `dedup.py` (find_duplicates, union-find clustering), `errors.py` (DedupError), `_validate.py` (argument checks).
- **Public API**: the names listed in `__all__` of `src/near_dup_detector/__init__.py`. Anything else is internal.
- **Errors**: invalid input raises `DedupError`, a `ValueError` subclass with a stable `code`.
- **Logging**: a module logger with a `NullHandler`; the library never configures logging and never logs input text.

## Quality contract

`scripts/check.py` is the single definition of the gates; `fabrica.json` tells the factory and CI how to run it. See [TESTING.md](TESTING.md).

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
