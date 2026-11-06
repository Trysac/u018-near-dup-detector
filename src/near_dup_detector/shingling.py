"""Text normalization and shingling."""

from __future__ import annotations

import unicodedata
from typing import Literal

from ._validate import require_int
from .errors import DedupError

DEFAULT_MAX_CHARS = 1_000_000


def normalize_text(text: str) -> str:
    """Apply NFKC, casefold, map non-alphanumerics to spaces and collapse whitespace."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in folded).split())


def shingles(
    text: str,
    *,
    k: int = 5,
    unit: Literal["word", "char"] = "word",
    max_chars: int = DEFAULT_MAX_CHARS,
) -> set[str]:
    """Return the set of ``k``-shingles of the normalized ``text``.

    Word shingles are ``k`` consecutive words joined by one space; character shingles are ``k``
    consecutive characters of the normalized text. A text shorter than ``k`` yields one shingle
    holding the whole normalized text; an empty text yields an empty set.

    Raises:
        DedupError: ``invalid_argument`` for bad parameters, ``input_too_large`` when ``text``
            has more than ``max_chars`` characters.
    """
    require_int("k", k, 1)
    require_int("max_chars", max_chars, 1)
    if unit not in ("word", "char"):
        raise DedupError("invalid_argument", "unit must be 'word' or 'char'")
    if not isinstance(text, str):
        raise DedupError("invalid_argument", "text must be a string")
    if len(text) > max_chars:
        raise DedupError("input_too_large", f"text exceeds max_chars={max_chars}")
    normalized = normalize_text(text)
    if not normalized:
        return set()
    if unit == "char":
        if len(normalized) < k:
            return {normalized}
        return {normalized[i : i + k] for i in range(len(normalized) - k + 1)}
    words = normalized.split(" ")
    if len(words) < k:
        return {normalized}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}
