"""Shared argument validation helpers."""

from __future__ import annotations

from .errors import DedupError

MAX_ID_CHARS = 1024


def require_int(name: str, value: object, minimum: int, maximum: int | None = None) -> int:
    """Return ``value`` when it is an ``int`` within bounds, else raise ``DedupError``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DedupError("invalid_argument", f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        bound = f">= {minimum}" if maximum is None else f"between {minimum} and {maximum}"
        raise DedupError("invalid_argument", f"{name} must be {bound}")
    return value


def check_seed(seed: object) -> int:
    """Validate a hash seed (a signed or unsigned 64-bit integer)."""
    return require_int("seed", seed, -(2**63), 2**64 - 1)


def check_doc_id(doc_id: object) -> str:
    """Validate a document id: a non-empty string of at most ``MAX_ID_CHARS`` characters."""
    if not isinstance(doc_id, str) or not doc_id:
        raise DedupError("invalid_argument", "document id must be a non-empty string")
    if len(doc_id) > MAX_ID_CHARS:
        raise DedupError("input_too_large", f"document id exceeds {MAX_ID_CHARS} characters")
    return doc_id
