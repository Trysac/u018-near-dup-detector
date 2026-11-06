"""MinHash signatures (Broder 1997) with universal hashing over the prime 2**61 - 1."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from hashlib import blake2b

from ._hashing import hash64
from ._validate import check_seed, require_int
from .errors import DedupError

MERSENNE_PRIME = (1 << 61) - 1
MAX_NUM_PERM = 65_536
MAX_ITEMS = 10_000_000


class MinHasher:
    """Compute seeded, process-stable MinHash signatures.

    Component ``i`` of a signature is ``min((a_i * h(x) + b_i) % p)`` over the items ``x``, with
    ``p = 2**61 - 1`` and ``h`` a 64-bit BLAKE2b hash. The standard error of the similarity
    estimate is about ``sqrt(J * (1 - J) / num_perm)`` for a true Jaccard index ``J``.
    """

    def __init__(self, num_perm: int = 128, seed: int = 1) -> None:
        self._num_perm = require_int("num_perm", num_perm, 1, MAX_NUM_PERM)
        self._seed = check_seed(seed)
        coefficients: list[tuple[int, int]] = []
        for i in range(self._num_perm):
            digest = blake2b(f"{self._seed}:{i}".encode(), digest_size=16).digest()
            a = int.from_bytes(digest[:8], "little") % (MERSENNE_PRIME - 1) + 1
            b = int.from_bytes(digest[8:], "little") % MERSENNE_PRIME
            coefficients.append((a, b))
        self._coefficients = tuple(coefficients)

    @property
    def num_perm(self) -> int:
        """Number of permutations (signature length)."""
        return self._num_perm

    @property
    def seed(self) -> int:
        """Seed the permutations were derived from."""
        return self._seed

    def signature(self, items: Iterable[str]) -> tuple[int, ...]:
        """Return the signature of a set of strings; an empty set gives a tuple of ``p``.

        Raises:
            DedupError: ``invalid_argument`` for non-string items or text that is not
                UTF-8 encodable, ``input_too_large`` above ``MAX_ITEMS`` items.
        """
        if isinstance(items, str | bytes):
            raise DedupError("invalid_argument", "items must be an iterable of strings")
        hashes: set[int] = set()
        for count, item in enumerate(items, start=1):
            if not isinstance(item, str):
                raise DedupError("invalid_argument", "every item must be a string")
            if count > MAX_ITEMS:
                raise DedupError("input_too_large", f"more than {MAX_ITEMS} items")
            hashes.add(hash64(item))
        minima = [MERSENNE_PRIME] * self._num_perm
        for hashed in hashes:
            for i, (a, b) in enumerate(self._coefficients):
                value = (a * hashed + b) % MERSENNE_PRIME
                if value < minima[i]:
                    minima[i] = value
        return tuple(minima)

    @staticmethod
    def similarity(a: Sequence[int], b: Sequence[int]) -> float:
        """Return the fraction of equal positions of two signatures.

        Raises:
            DedupError: ``invalid_argument`` when the lengths differ or are zero.
        """
        if len(a) != len(b):
            raise DedupError("invalid_argument", "signatures must have the same length")
        if not a:
            raise DedupError("invalid_argument", "signatures must not be empty")
        matches = sum(1 for x, y in zip(a, b, strict=True) if x == y)
        return matches / len(a)
