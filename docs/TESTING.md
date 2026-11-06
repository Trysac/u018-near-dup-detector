# Testing

## Running

```sh
uv run pytest --cov=near_dup_detector   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Existing tests

- `tests/test_near_dup_detector.py`: exercises the public API (`import near_dup_detector`) for shingling, MinHasher signatures and similarity, LSHIndex add/candidates/remove and its errors, simhash, and find_duplicates clustering with its `invalid_argument`, `input_too_large` and `DedupError` codes.

The acceptance literals in the specification (for example the MinHash tuple and SimHash value) are asserted in that file but were not executed when this documentation was written.

## Policy

- Branch coverage of `src/near_dup_detector` must stay at or above 80 %; the gate fails below it.
- Tests assert return values, raised exceptions and their codes.
- Each bug fix starts with a failing test that reproduces it.
- Tests are deterministic: no network, no wall clock, no dependence on test order.

## Layout

`tests/test_<module>.py` mirrors each public module. Shared fixtures go in `tests/conftest.py`, which is not present yet.
