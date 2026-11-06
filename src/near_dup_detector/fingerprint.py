"""SimHash fingerprints (Charikar 2002)."""

from __future__ import annotations

from collections.abc import Iterable

from ._hashing import hash64
from ._validate import require_int
from .errors import DedupError

MAX_TOKENS = 10_000_000


def simhash(tokens: Iterable[str], *, bits: int = 64) -> int:
    """Return the SimHash of ``tokens`` as an integer of ``bits`` bits.

    Each token is hashed to 64 bits with BLAKE2b. Bit ``i`` of the result is set when strictly
    more than half of the tokens, duplicates counted, have bit ``i`` set. Short token lists give
    noisy fingerprints. Compare fingerprints with ``(a ^ b).bit_count()``.

    Raises:
        DedupError: ``invalid_argument`` for bad parameters or non-string tokens,
            ``input_too_large`` above ``MAX_TOKENS`` tokens.
    """
    require_int("bits", bits, 1, 64)
    if isinstance(tokens, str | bytes):
        raise DedupError("invalid_argument", "tokens must be an iterable of strings")
    counts: dict[str, int] = {}
    total = 0
    for token in tokens:
        if not isinstance(token, str):
            raise DedupError("invalid_argument", "every token must be a string")
        total += 1
        if total > MAX_TOKENS:
            raise DedupError("input_too_large", f"more than {MAX_TOKENS} tokens")
        counts[token] = counts.get(token, 0) + 1
    ones = [0] * bits
    for token, multiplicity in counts.items():
        hashed = hash64(token)
        for i in range(bits):
            if (hashed >> i) & 1:
                ones[i] += multiplicity
    result = 0
    for i, count in enumerate(ones):
        if 2 * count > total:
            result |= 1 << i
    return result
