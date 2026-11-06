"""Detect near-duplicate documents with process-stable MinHash, LSH banding and SimHash."""

from __future__ import annotations

import logging

from .dedup import DuplicateCluster, find_duplicates
from .errors import DedupError
from .fingerprint import simhash
from .lsh import LSHIndex
from .minhash import MinHasher
from .shingling import shingles

__all__ = [
    "DedupError",
    "DuplicateCluster",
    "LSHIndex",
    "MinHasher",
    "__version__",
    "find_duplicates",
    "shingles",
    "simhash",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
