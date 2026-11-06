"""Duplicate detection: fingerprints, candidate generation, verification and clustering."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Literal

from ._validate import check_doc_id, check_seed, require_int
from .errors import DedupError
from .fingerprint import simhash
from .lsh import LSHIndex
from .minhash import MinHasher
from .shingling import shingles

logger = logging.getLogger(__name__)

MAX_DOCUMENTS = 100_000
_NUM_PERM = 128
_SIMHASH_BITS = 64


@dataclass(frozen=True)
class DuplicateCluster:
    """A group of near-duplicate documents.

    Attributes:
        ids: Sorted document ids of the cluster (at least two).
        representative: The smallest id of the cluster.
        min_similarity: The smallest verified edge similarity inside the cluster.
    """

    ids: tuple[str, ...]
    representative: str
    min_similarity: float


class _Clusters:
    """Union-find over document ids tracking the weakest verified edge of each cluster."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._weakest: dict[str, float] = {}

    def add(self, doc_id: str) -> None:
        self._parent[doc_id] = doc_id
        self._weakest[doc_id] = float("inf")

    def _find(self, doc_id: str) -> str:
        root = doc_id
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[doc_id] != root:
            following = self._parent[doc_id]
            self._parent[doc_id] = root
            doc_id = following
        return root

    def link(self, first: str, second: str, similarity: float) -> None:
        root_a = self._find(first)
        root_b = self._find(second)
        if root_a == root_b:
            self._weakest[root_a] = min(self._weakest[root_a], similarity)
            return
        self._parent[root_b] = root_a
        self._weakest[root_a] = min(self._weakest[root_a], self._weakest[root_b], similarity)

    def result(self) -> list[DuplicateCluster]:
        groups: dict[str, list[str]] = {}
        for doc_id in self._parent:
            groups.setdefault(self._find(doc_id), []).append(doc_id)
        clusters: list[DuplicateCluster] = []
        for root, members in groups.items():
            if len(members) < 2:
                continue
            ids = tuple(sorted(members))
            clusters.append(
                DuplicateCluster(
                    ids=ids,
                    representative=ids[0],
                    min_similarity=self._weakest[root],
                )
            )
        clusters.sort(key=lambda cluster: cluster.ids)
        return clusters


def _check_threshold(threshold: object) -> float:
    if isinstance(threshold, bool) or not isinstance(threshold, int | float):
        raise DedupError("invalid_argument", "threshold must be a number")
    if not 0 < threshold <= 1:
        raise DedupError("invalid_argument", "threshold must be in (0, 1]")
    return float(threshold)


def _choose_banding(num_perm: int, threshold: float) -> tuple[int, int]:
    """Pick ``(bands, rows)`` whose LSH threshold is the largest one not above ``threshold``."""
    best: tuple[float, int, int] | None = None
    for rows in range(1, num_perm + 1):
        if num_perm % rows:
            continue
        bands = num_perm // rows
        estimate = (1 / bands) ** (1 / rows)
        if estimate <= threshold and (best is None or estimate > best[0]):
            best = (estimate, bands, rows)
    if best is None:
        return (num_perm, 1)
    return (best[1], best[2])


def _iter_shingle_sets(
    docs: Mapping[str, str], ids: list[str], k: int
) -> Iterator[tuple[str, set[str]]]:
    for doc_id in ids:
        text = docs[doc_id]
        if not isinstance(text, str):
            raise DedupError("invalid_argument", "every document must be a string")
        items = shingles(text, k=k)
        if items:
            yield doc_id, items


def _link_minhash(
    entries: Iterator[tuple[str, set[str]]],
    clusters: _Clusters,
    threshold: float,
    seed: int,
    total: int,
) -> None:
    hasher = MinHasher(_NUM_PERM, seed)
    bands, rows = _choose_banding(_NUM_PERM, threshold)
    index = LSHIndex(num_perm=_NUM_PERM, bands=bands, rows=rows, max_entries=max(total, 1))
    signatures: dict[str, tuple[int, ...]] = {}
    for doc_id, items in entries:
        signature = hasher.signature(items)
        clusters.add(doc_id)
        for other in sorted(index.candidates(signature)):
            similarity = MinHasher.similarity(signature, signatures[other])
            if similarity >= threshold:
                clusters.link(other, doc_id, similarity)
        index.add(doc_id, signature)
        signatures[doc_id] = signature


def _block_keys(fingerprint: int, spans: list[tuple[int, int]]) -> list[int]:
    return [(fingerprint >> low) & ((1 << (high - low)) - 1) for low, high in spans]


def _link_simhash(
    entries: Iterator[tuple[str, set[str]]],
    clusters: _Clusters,
    max_hamming: int,
) -> None:
    # Pigeonhole: fingerprints within max_hamming bits agree on at least one of max_hamming + 1
    # blocks, so equal-block buckets contain every true match.
    blocks = max_hamming + 1
    spans = [
        (b * _SIMHASH_BITS // blocks, (b + 1) * _SIMHASH_BITS // blocks) for b in range(blocks)
    ]
    tables: list[dict[int, list[str]]] = [{} for _ in spans]
    fingerprints: dict[str, int] = {}
    for doc_id, items in entries:
        fingerprint = simhash(sorted(items), bits=_SIMHASH_BITS)
        clusters.add(doc_id)
        keys = _block_keys(fingerprint, spans)
        found: set[str] = set()
        for key, table in zip(keys, tables, strict=True):
            found.update(table.get(key, ()))
        for other in sorted(found):
            distance = (fingerprint ^ fingerprints[other]).bit_count()
            if distance <= max_hamming:
                clusters.link(other, doc_id, 1 - distance / _SIMHASH_BITS)
        for key, table in zip(keys, tables, strict=True):
            table.setdefault(key, []).append(doc_id)
        fingerprints[doc_id] = fingerprint


def find_duplicates(
    docs: Mapping[str, str],
    *,
    threshold: float = 0.8,
    method: Literal["minhash", "simhash"] = "minhash",
    k: int = 5,
    seed: int = 1,
    max_hamming: int = 3,
) -> list[DuplicateCluster]:
    """Group near-duplicate documents into deterministic clusters.

    With ``method='minhash'`` documents are fingerprinted with 128-permutation MinHash over their
    word shingles, candidates come from LSH banding and a pair is kept when its signature
    similarity is at least ``threshold``. With ``method='simhash'`` the sorted shingle set is the
    token list of a 64-bit SimHash and a pair is kept when the Hamming distance is at most
    ``max_hamming`` (its similarity is ``1 - hamming / 64``; ``threshold`` is not used).
    Verified pairs are merged with union-find. Clusters are sorted by ids, singletons are not
    returned and documents whose shingle set is empty are skipped.

    Raises:
        DedupError: ``invalid_argument`` for bad parameters or documents, ``input_too_large``
            for more than ``MAX_DOCUMENTS`` documents or a document over one million characters.
    """
    if not isinstance(docs, Mapping):
        raise DedupError("invalid_argument", "docs must be a mapping of id to text")
    limit = _check_threshold(threshold)
    if method not in ("minhash", "simhash"):
        raise DedupError("invalid_argument", "method must be 'minhash' or 'simhash'")
    require_int("k", k, 1)
    check_seed(seed)
    require_int("max_hamming", max_hamming, 0, _SIMHASH_BITS - 1)
    if len(docs) > MAX_DOCUMENTS:
        raise DedupError("input_too_large", f"more than {MAX_DOCUMENTS} documents")
    ids = sorted(check_doc_id(doc_id) for doc_id in docs)
    clusters = _Clusters()
    entries = _iter_shingle_sets(docs, ids, k)
    if method == "minhash":
        _link_minhash(entries, clusters, limit, seed, len(ids))
    else:
        _link_simhash(entries, clusters, max_hamming)
    result = clusters.result()
    logger.debug("find_duplicates: %d documents, %d clusters", len(ids), len(result))
    return result
