# Process-stable MinHash/SimHash with banded LSH, verification and union-find clustering

Status: accepted (generated, pending human review)

## Context

Feeds and scraped collections contain the same text with small edits. Exact hashing misses them, pairwise comparison is quadratic and Python's built-in hash() differs per process, which makes fingerprints irreproducible. The library must be pure Python with no runtime dependency, deterministic, and must bound untrusted input.

## Decision

Fingerprints use BLAKE2b (never hash()): MinHash with universal hashing modulo 2**61 - 1 and coefficients derived from the seed, and 64-bit SimHash. LSH banding finds candidates, which are always verified (signature similarity against the threshold, or Hamming distance against max_hamming) before union-find clustering. find_duplicates picks the (bands, rows) split of 128 permutations whose LSH threshold is the largest one not above the requested threshold, and SimHash candidates come from max_hamming + 1 fingerprint blocks (pigeonhole). Clusters are sorted, the representative is the smallest id and min_similarity is the weakest verified edge. All inputs are bounded and every failure is a DedupError with a stable code.

## Consequences

Results are identical across processes and platforms and need no dependency such as numpy. Candidate generation is sub-quadratic except inside very large clusters, where every candidate pair is verified. Pure-Python hashing is slower than vectorized implementations, and SimHash on short texts is noisy. Threshold-adaptive banding keeps recall for low thresholds at the price of more candidates to verify. Persistence, streaming at scale and semantic duplicates are out of scope.
