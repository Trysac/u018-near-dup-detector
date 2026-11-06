# near-dup-detector

[![PyPI version](https://img.shields.io/pypi/v/trysac-near-dup-detector)](https://pypi.org/project/trysac-near-dup-detector/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-near-dup-detector)](LICENSE)
[![CI](https://github.com/Trysac/u018-near-dup-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u018-near-dup-detector/actions/workflows/ci.yml)

Detect near-duplicate documents with process-stable MinHash and LSH banding plus 64-bit SimHash, verified candidate pairs and deterministic clusters

## Problem

Feeds, scraped pages and document collections often contain the same text with small edits. Exact hashing misses these near-duplicates, and pairwise comparison is quadratic, so duplicates inflate indexes and bias retrieval. Python's built-in hash gives different results per process, so fingerprints cannot be reused across runs. This library fingerprints documents with seeded, process-stable MinHash and SimHash, finds candidates with LSH banding, verifies them and groups duplicates deterministically.

## Install

```sh
pip install trysac-near-dup-detector
# or
uv add trysac-near-dup-detector
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from near_dup_detector import find_duplicates

t = "the quick brown fox jumps over the lazy dog"
docs = {"b": t, "a": t, "c": "lorem ipsum dolor sit amet consectetur adipiscing elit", "e": ""}
for cluster in find_duplicates(docs):
    print(cluster.ids, cluster.representative, cluster.min_similarity)
# ('a', 'b') a 1.0
```

## Public API

- `shingles(text, *, k=5, unit='word', max_chars=1_000_000) -> set[str]`: NFKC, casefold, non-alphanumerics to spaces, then k-shingles. Raises `input_too_large` above `max_chars`.
- `MinHasher(num_perm=128, seed=1)`: `signature(items) -> tuple[int, ...]`; `MinHasher.similarity(a, b) -> float`. Length mismatch raises `invalid_argument`.
- `LSHIndex(*, num_perm=128, bands=16, rows=8, max_entries=1_000_000)`: `add(doc_id, signature)`, `candidates(signature) -> set[str]`, `remove(doc_id) -> bool`. Raises `duplicate_id` and `index_full`.
- `simhash(tokens, *, bits=64) -> int`: compare with `(a ^ b).bit_count()`.
- `find_duplicates(docs, *, threshold=0.8, method='minhash', k=5, seed=1, max_hamming=3) -> list[DuplicateCluster]`. `method='simhash'` ignores `threshold`; `max_hamming` must be 0 to 63.
- `DuplicateCluster`: frozen dataclass with `ids`, `representative`, `min_similarity`. Singletons are not returned; empty texts are skipped.
- `DedupError(ValueError)` with `code` in `invalid_argument`, `duplicate_id`, `input_too_large`, `index_full`.

Limits: `num_perm <= 65536`; seeds within a 64-bit range; at most 10,000,000 items or tokens per fingerprint; document ids of 1 to 1024 characters; at most 100,000 documents per `find_duplicates` call.

## Why not datasketch

datasketch depends on numpy. This library is a pure-Python, process-stable subset with verification and clustering.

## Security

See [docs/SECURITY.md](docs/SECURITY.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
