"""Locality-sensitive hashing index (banding) over MinHash signatures."""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import blake2b

from ._validate import check_doc_id, require_int
from .errors import DedupError

_VALUE_LIMIT = 1 << 64


class LSHIndex:
    """In-memory banded LSH index.

    Band ``j`` hashes the rows ``j * rows`` to ``j * rows + rows - 1`` of a signature. Two
    documents with similarity ``s`` collide in at least one band with probability
    ``1 - (1 - s**rows)**bands``. Candidates are not verified; compare signatures afterwards.
    The index holds at most ``max_entries`` documents.
    """

    def __init__(
        self,
        *,
        num_perm: int = 128,
        bands: int = 16,
        rows: int = 8,
        max_entries: int = 1_000_000,
    ) -> None:
        self._num_perm = require_int("num_perm", num_perm, 1)
        self._bands = require_int("bands", bands, 1)
        self._rows = require_int("rows", rows, 1)
        self._max_entries = require_int("max_entries", max_entries, 1)
        if self._bands * self._rows != self._num_perm:
            raise DedupError("invalid_argument", "bands * rows must equal num_perm")
        self._buckets: list[dict[bytes, set[str]]] = [{} for _ in range(self._bands)]
        self._doc_keys: dict[str, tuple[bytes, ...]] = {}

    def __len__(self) -> int:
        return len(self._doc_keys)

    def __contains__(self, doc_id: object) -> bool:
        return doc_id in self._doc_keys

    def _band_keys(self, signature: Sequence[int]) -> tuple[bytes, ...]:
        if isinstance(signature, str | bytes) or not isinstance(signature, Sequence):
            raise DedupError("invalid_argument", "signature must be a sequence of integers")
        if len(signature) != self._num_perm:
            raise DedupError("invalid_argument", "signature length must equal num_perm")
        for value in signature:
            valid = isinstance(value, int) and not isinstance(value, bool)
            if not valid or not 0 <= value < _VALUE_LIMIT:
                raise DedupError("invalid_argument", "signature values must be 64-bit integers")
        keys: list[bytes] = []
        for band in range(self._bands):
            chunk = signature[band * self._rows : (band + 1) * self._rows]
            payload = b"".join(value.to_bytes(8, "little") for value in chunk)
            keys.append(blake2b(payload, digest_size=16).digest())
        return tuple(keys)

    def add(self, doc_id: str, signature: Sequence[int]) -> None:
        """Index ``signature`` under ``doc_id``.

        Raises:
            DedupError: ``invalid_argument`` for a bad id or signature, ``duplicate_id`` when
                the id is already indexed, ``index_full`` when ``max_entries`` is reached.
        """
        check_doc_id(doc_id)
        keys = self._band_keys(signature)
        if doc_id in self._doc_keys:
            raise DedupError("duplicate_id", "document id is already indexed")
        if len(self._doc_keys) >= self._max_entries:
            raise DedupError("index_full", "index has reached max_entries")
        for band, key in enumerate(keys):
            self._buckets[band].setdefault(key, set()).add(doc_id)
        self._doc_keys[doc_id] = keys

    def candidates(self, signature: Sequence[int]) -> set[str]:
        """Return the ids of indexed documents sharing at least one band with ``signature``."""
        found: set[str] = set()
        for band, key in enumerate(self._band_keys(signature)):
            found.update(self._buckets[band].get(key, ()))
        return found

    def remove(self, doc_id: str) -> bool:
        """Remove ``doc_id`` from the index; return ``False`` when it was not indexed."""
        keys = self._doc_keys.pop(doc_id, None)
        if keys is None:
            return False
        for band, key in enumerate(keys):
            bucket = self._buckets[band][key]
            bucket.discard(doc_id)
            if not bucket:
                del self._buckets[band][key]
        return True
