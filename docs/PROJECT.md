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
| Tokens (input / output) | 474700 / 74839 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.6725 |

## Factory run u018 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2428 | 61711 | 0 | 4246 | 0.3114 |
| fix-1 | claude-sonnet-5-5 | no | 6 | 1192 | 7670 | 41710 | 0.0353 |
| fix-2 | claude-sonnet-5-5 | no | 12 | 1994 | 7912 | 87442 | 0.0485 |
| fix-3 | claude-sonnet-5-5 | no | 6 | 913 | 7340 | 40976 | 0.0316 |
| fix-4 | claude-sonnet-5-5 | no | 8 | 1279 | 9202 | 58783 | 0.0417 |
| audit | claude-sonnet-5-5 | no | 12 | 3320 | 36893 | 130033 | 0.1385 |
| docs | claude-haiku-5-5 | no | 109038 | 4430 | 0 | 0 | 0.0656 |

Total: $0.6725. Prices: Anthropic list prices.
