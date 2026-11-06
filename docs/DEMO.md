# Demo: near-duplicate detection

This walkthrough uses only the public API of `near_dup_detector`. Every printed value below is
exact and deterministic: the library never calls the built-in `hash()`, so results are the same in
every process.

## Normalization and shingles

Text is normalized with NFKC, casefolded, every non-alphanumeric character becomes a space and
whitespace is collapsed. Word shingles are `k` consecutive words joined by one space.

```python
from near_dup_detector import shingles

print(sorted(shingles("Hello,  World! hello world", k=2)))
# ['hello world', 'world hello']
```

Text shorter than `k` gives one shingle holding the whole text; empty text gives an empty set.

## Finding duplicate clusters

```python
from near_dup_detector import find_duplicates

t = "the quick brown fox jumps over the lazy dog"
t2 = "lorem ipsum dolor sit amet consectetur adipiscing elit"
docs = {"b": t, "a": t, "c": t2, "e": "", "f": ""}
print(find_duplicates(docs))
# [DuplicateCluster(ids=('a', 'b'), representative='a', min_similarity=1.0)]
```

Clusters are sorted by ids, the representative is the smallest id, singletons are not returned and
documents with no shingles (empty texts) are never clustered.

## Building blocks

```python
from near_dup_detector import LSHIndex, MinHasher, shingles, simhash

hasher = MinHasher(num_perm=128, seed=1)
index = LSHIndex(num_perm=128, bands=16, rows=8)
index.add("doc-1", hasher.signature(shingles("some long document text ...")))
candidates = index.candidates(hasher.signature(shingles("some long document text ...")))
print(candidates)  # {'doc-1'}
print(simhash(["a", "b", "c"]) == 0x3F4E074D61C27A04)  # True
```

## How it works

- **MinHash** (Broder 1997): universal hashing modulo `p = 2**61 - 1` over a 64-bit BLAKE2b hash
  of each shingle; the coefficients of permutation `i` derive from `blake2b(f"{seed}:{i}")`.
  The standard error of the estimate is about `sqrt(J * (1 - J) / num_perm)`.
- **LSH banding**: band `j` hashes rows `j * r` to `j * r + r - 1`. Two documents with similarity
  `s` become candidates with probability `1 - (1 - s**r)**b`; the defaults (16 bands of 8 rows)
  put the threshold near `(1/16)**(1/8)`, about 0.71. Candidates are verified with the signature
  estimate before they are clustered.
- **SimHash** (Charikar 2002): bit `i` is set when more than half of the tokens, duplicates
  counted, have bit `i` set. Short texts are noisy. `find_duplicates(method="simhash")` hashes the
  sorted shingle set, accepts pairs within `max_hamming` bits (default 3, following Manku, Jain and
  Das Sarma, WWW 2007) and finds candidates with `max_hamming + 1` blocks of the fingerprint
  (pigeonhole principle), so it never compares all pairs.
- **Banding choice in `find_duplicates`**: with 128 permutations the `(bands, rows)` split whose
  LSH threshold is the largest one not above `threshold` is used. The default threshold of 0.8
  therefore uses 16 bands of 8 rows.
- **Clustering**: union-find over verified pairs. `min_similarity` is the smallest verified edge
  similarity of the cluster (for SimHash, `1 - hamming / 64`).

## Limits and errors

Every failure raises `DedupError` (a `ValueError`) with a stable `code`:
`invalid_argument`, `duplicate_id`, `input_too_large` or `index_full`. Messages never contain more
than 200 characters and never echo document text.

| Limit | Default | Error |
|---|---|---|
| `shingles(max_chars=...)` text length | 1,000,000 characters | `input_too_large` |
| `LSHIndex(max_entries=...)` documents | 1,000,000 | `index_full` |
| documents per `find_duplicates` call | 100,000 | `input_too_large` |
| items per `MinHasher.signature`, tokens per `simhash` | 10,000,000 | `input_too_large` |
| `MinHasher(num_perm=...)` | at most 65,536 | `invalid_argument` |
| document id length | 1 to 1,024 characters | `invalid_argument` / `input_too_large` |

A cluster of many identical documents verifies every candidate pair inside it, so the worst case
of `find_duplicates` is quadratic in the size of the largest cluster.

The library never configures logging (it installs a `NullHandler` on its package logger) and logs
only document and cluster counts at debug level, never input text.

Out of scope: persistence, streaming at scale, embedding-based semantic duplicates and language
detection.
