"""Process-stable 64-bit string hashing (never the built-in ``hash``)."""

from __future__ import annotations

from hashlib import blake2b

from .errors import DedupError


def hash64(value: str) -> int:
    """Return the little-endian 64-bit BLAKE2b digest of the UTF-8 encoding of ``value``."""
    try:
        data = value.encode("utf-8")
    except UnicodeEncodeError:
        raise DedupError("invalid_argument", "text is not encodable as UTF-8") from None
    return int.from_bytes(blake2b(data, digest_size=8).digest(), "little")
