"""Tests for the near_dup_detector public API."""

from __future__ import annotations

import copy
import importlib
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import near_dup_detector
from near_dup_detector import (
    DedupError,
    DuplicateCluster,
    LSHIndex,
    MinHasher,
    find_duplicates,
    shingles,
    simhash,
)

dedup_module = importlib.import_module("near_dup_detector.dedup")
fingerprint_module = importlib.import_module("near_dup_detector.fingerprint")
minhash_module = importlib.import_module("near_dup_detector.minhash")

EXPECTED_SIGNATURE = (
    195814214256583273,
    1323040718152789041,
    553596664185966134,
    78966908916426969,
)

T = "the quick brown fox jumps over the lazy dog"
T2 = "lorem ipsum dolor sit amet consectetur adipiscing elit"


def raises_code(code: str, call: Callable[[], object]) -> None:
    with pytest.raises(DedupError) as info:
        call()
    assert info.value.code == code


def words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(count))


def spread_variant() -> str:
    tokens = [f"word{i}" for i in range(200)]
    for position in range(10, 200, 20):
        tokens[position] = f"changed{position}"
    return " ".join(tokens)


# --- package ---------------------------------------------------------------------------------


def test_version_and_null_handler() -> None:
    assert near_dup_detector.__version__ == "0.1.0"
    handlers = logging.getLogger("near_dup_detector").handlers
    assert any(isinstance(handler, logging.NullHandler) for handler in handlers)


def test_error_is_value_error_with_code_and_truncated_message() -> None:
    error = DedupError("invalid_argument", "x" * 500)
    assert isinstance(error, ValueError)
    assert error.code == "invalid_argument"
    assert len(str(error)) == 200


def test_error_survives_copy() -> None:
    clone = copy.deepcopy(DedupError("index_full", "full"))
    assert isinstance(clone, DedupError)
    assert clone.code == "index_full"
    assert str(clone) == "full"


# --- shingles --------------------------------------------------------------------------------


def test_shingles_acceptance() -> None:
    assert shingles("Hello,  World! hello world", k=2) == {"hello world", "world hello"}


def test_shingles_char_unit() -> None:
    assert shingles("ab cd", k=3, unit="char") == {"ab ", "b c", " cd"}


def test_shingles_short_text_gives_whole_text() -> None:
    assert shingles("Hi there", k=5) == {"hi there"}
    assert shingles("ab", k=5, unit="char") == {"ab"}


def test_shingles_empty_text_gives_empty_set() -> None:
    assert shingles("") == set()
    assert shingles("  !!! ") == set()
    assert shingles("", unit="char") == set()


def test_shingles_unicode_normalization() -> None:
    assert shingles("\uff21\uff22\uff23 def", k=2) == {"abc def"}
    assert shingles("Stra\u00dfe", k=1) == {"strasse"}
    assert shingles("\ufb01le", k=1) == {"file"}


def test_shingles_punctuation_neighbours() -> None:
    assert shingles("a_b-c", k=1) == {"a", "b", "c"}
    assert shingles("v2.0-beta", k=1) == {"v2", "0", "beta"}
    assert shingles("3km,5kg", k=1) == {"3km", "5kg"}


def test_shingles_default_k_is_five() -> None:
    assert len(shingles("a b c d e f g")) == 3


def test_shingles_invalid_arguments() -> None:
    raises_code("invalid_argument", lambda: shingles("a b", k=0))
    raises_code("invalid_argument", lambda: shingles("a b", k=True))
    raises_code("invalid_argument", lambda: shingles("a b", max_chars=0))
    raises_code("invalid_argument", lambda: shingles("a b", unit="line"))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: shingles(b"a b"))  # type: ignore[arg-type]


def test_shingles_size_limit() -> None:
    raises_code("input_too_large", lambda: shingles("abcdef", max_chars=5))
    assert shingles("abcde", k=1, max_chars=5) == {"abcde"}
    raises_code("input_too_large", lambda: shingles("x" * 1_000_001))


# --- MinHasher -------------------------------------------------------------------------------


def test_minhash_acceptance_signature() -> None:
    assert MinHasher(num_perm=4, seed=1).signature({"a"}) == EXPECTED_SIGNATURE


def test_minhash_signature_is_process_stable() -> None:
    subprocess = importlib.import_module("subprocess")
    source = str(Path(__file__).resolve().parents[1] / "src")
    env = {**os.environ, "PYTHONHASHSEED": "123", "PYTHONPATH": source}
    code = (
        "from near_dup_detector import MinHasher; "
        "print(MinHasher(num_perm=4, seed=1).signature({'a'}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert completed.stdout.strip() == str(EXPECTED_SIGNATURE)


def test_minhash_seed_changes_signature() -> None:
    assert MinHasher(num_perm=4, seed=2).signature({"a"}) != EXPECTED_SIGNATURE
    assert MinHasher(num_perm=4, seed=-5).signature({"a"}) != EXPECTED_SIGNATURE


def test_minhash_properties() -> None:
    hasher = MinHasher(num_perm=8, seed=7)
    assert hasher.num_perm == 8
    assert hasher.seed == 7
    assert len(hasher.signature({"a", "b"})) == 8


def test_minhash_empty_set_gives_prime() -> None:
    assert MinHasher(num_perm=4).signature([]) == (2**61 - 1,) * 4


def test_minhash_ignores_order_and_duplicates() -> None:
    hasher = MinHasher(num_perm=16)
    assert hasher.signature(["a", "b", "a"]) == hasher.signature(["b", "a"])
    assert hasher.signature(["a", "a"]) == hasher.signature({"a"})


def test_minhash_estimate_is_close_to_jaccard() -> None:
    base = {f"s{i}" for i in range(100)}
    pairs = [
        (base, base),
        (base, {f"d{i}" for i in range(100)}),
        (base, base | {"extra"}),
        (base, {f"s{i}" for i in range(90)}),
        (base, {f"s{i}" for i in range(10)} | {f"n{i}" for i in range(90)}),
    ]
    hasher = MinHasher(num_perm=128, seed=1)
    for left, right in pairs:
        exact = len(left & right) / len(left | right)
        estimate = MinHasher.similarity(hasher.signature(left), hasher.signature(right))
        assert abs(estimate - exact) <= 0.1


def test_minhash_similarity() -> None:
    assert MinHasher.similarity((1, 2, 3, 4), (1, 2, 3, 4)) == 1.0
    assert MinHasher.similarity((1, 2, 3, 4), (1, 2, 0, 0)) == 0.5
    assert MinHasher.similarity([1], [2]) == 0.0


def test_minhash_similarity_errors() -> None:
    raises_code("invalid_argument", lambda: MinHasher.similarity((1, 2), (1,)))
    raises_code("invalid_argument", lambda: MinHasher.similarity((), ()))


def test_minhash_invalid_arguments() -> None:
    raises_code("invalid_argument", lambda: MinHasher(num_perm=0))
    raises_code("invalid_argument", lambda: MinHasher(num_perm=65_537))
    raises_code("invalid_argument", lambda: MinHasher(num_perm=True))
    raises_code("invalid_argument", lambda: MinHasher(seed="1"))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: MinHasher(seed=2**64))
    raises_code("invalid_argument", lambda: MinHasher(seed=True))


def test_minhash_invalid_items() -> None:
    hasher = MinHasher(num_perm=2)
    raises_code("invalid_argument", lambda: hasher.signature("abc"))
    raises_code("invalid_argument", lambda: hasher.signature(["a", 1]))  # type: ignore[list-item]
    raises_code("invalid_argument", lambda: hasher.signature(["\ud800"]))


def test_minhash_item_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minhash_module, "MAX_ITEMS", 2)
    hasher = MinHasher(num_perm=2)
    assert len(hasher.signature(["a", "b"])) == 2
    raises_code("input_too_large", lambda: hasher.signature(["a", "b", "c"]))


# --- LSHIndex --------------------------------------------------------------------------------


def test_lsh_candidates_near_duplicate_but_not_unrelated() -> None:
    hasher = MinHasher(num_perm=128, seed=1)
    base = words("word", 200)
    near = base.replace("word100", "changed")
    other = words("other", 200)
    index = LSHIndex(num_perm=128, bands=16, rows=8)
    index.add("base", hasher.signature(shingles(base)))
    index.add("other", hasher.signature(shingles(other)))
    assert index.candidates(hasher.signature(shingles(near))) == {"base"}
    assert index.candidates(hasher.signature(shingles(base))) == {"base"}
    assert len(index) == 2
    assert "base" in index
    assert "near" not in index


def test_lsh_bands_times_rows_must_equal_num_perm() -> None:
    raises_code("invalid_argument", lambda: LSHIndex(num_perm=128, bands=16, rows=7))


def test_lsh_invalid_constructor_arguments() -> None:
    raises_code("invalid_argument", lambda: LSHIndex(num_perm=0, bands=1, rows=1))
    raises_code("invalid_argument", lambda: LSHIndex(bands=0))
    raises_code("invalid_argument", lambda: LSHIndex(rows=0))
    raises_code("invalid_argument", lambda: LSHIndex(max_entries=0))


def test_lsh_duplicate_id() -> None:
    index = LSHIndex(num_perm=4, bands=2, rows=2)
    index.add("a", (1, 2, 3, 4))
    raises_code("duplicate_id", lambda: index.add("a", (1, 2, 3, 4)))
    assert len(index) == 1


def test_lsh_index_full_and_remove_frees_capacity() -> None:
    index = LSHIndex(num_perm=4, bands=2, rows=2, max_entries=1)
    index.add("a", (1, 2, 3, 4))
    raises_code("index_full", lambda: index.add("b", (5, 6, 7, 8)))
    assert index.remove("a") is True
    assert index.remove("a") is False
    assert index.candidates((1, 2, 3, 4)) == set()
    index.add("b", (5, 6, 7, 8))
    assert index.candidates((5, 6, 9, 9)) == {"b"}


def test_lsh_remove_keeps_other_documents_in_shared_buckets() -> None:
    index = LSHIndex(num_perm=4, bands=2, rows=2)
    index.add("a", (1, 2, 3, 4))
    index.add("b", (1, 2, 5, 6))
    assert index.candidates((1, 2, 0, 0)) == {"a", "b"}
    assert index.remove("a") is True
    assert index.candidates((1, 2, 0, 0)) == {"b"}


def test_lsh_invalid_signatures() -> None:
    index = LSHIndex(num_perm=4, bands=2, rows=2)
    raises_code("invalid_argument", lambda: index.add("a", (1, 2, 3)))
    raises_code("invalid_argument", lambda: index.add("a", (1, 2, 3, -1)))
    raises_code("invalid_argument", lambda: index.add("a", (1, 2, 3, 2**64)))
    raises_code("invalid_argument", lambda: index.add("a", (1, 2, 3, True)))
    raises_code("invalid_argument", lambda: index.add("a", (1, 2, 3, "4")))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: index.add("a", "abcd"))
    raises_code("invalid_argument", lambda: index.candidates(iter((1, 2, 3, 4))))  # type: ignore[arg-type]
    assert len(index) == 0


def test_lsh_invalid_ids() -> None:
    index = LSHIndex(num_perm=4, bands=2, rows=2)
    raises_code("invalid_argument", lambda: index.add("", (1, 2, 3, 4)))
    raises_code("invalid_argument", lambda: index.add(5, (1, 2, 3, 4)))  # type: ignore[arg-type]
    raises_code("input_too_large", lambda: index.add("x" * 1025, (1, 2, 3, 4)))


# --- simhash ---------------------------------------------------------------------------------


def test_simhash_acceptance() -> None:
    assert simhash(["a", "b", "c"]) == 0x3F4E074D61C27A04
    a = [f"w{i}" for i in range(50)]
    b = [*a[:-1], "x"]
    c = [f"z{i}" for i in range(50)]
    assert (simhash(a) ^ simhash(b)).bit_count() == 5
    assert (simhash(a) ^ simhash(c)).bit_count() == 34


def test_simhash_bits_and_empty() -> None:
    assert simhash(["a", "b", "c"], bits=8) == 0x04
    assert simhash([]) == 0
    assert simhash(["a"], bits=1) in (0, 1)


def test_simhash_counts_duplicates() -> None:
    assert simhash(["a", "a", "b"]) == simhash(["a"])


def test_simhash_invalid_arguments() -> None:
    raises_code("invalid_argument", lambda: simhash(["a"], bits=0))
    raises_code("invalid_argument", lambda: simhash(["a"], bits=65))
    raises_code("invalid_argument", lambda: simhash("abc"))
    raises_code("invalid_argument", lambda: simhash(["a", 1]))  # type: ignore[list-item]
    raises_code("invalid_argument", lambda: simhash(["\ud800"]))


def test_simhash_token_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fingerprint_module, "MAX_TOKENS", 2)
    assert simhash(["a", "b"]) >= 0
    raises_code("input_too_large", lambda: simhash(["a", "b", "c"]))


# --- find_duplicates -------------------------------------------------------------------------


def test_find_duplicates_acceptance() -> None:
    docs = {"b": T, "a": T, "c": T2, "e": "", "f": ""}
    assert find_duplicates(docs) == [
        DuplicateCluster(ids=("a", "b"), representative="a", min_similarity=1.0)
    ]


def test_find_duplicates_clusters_are_sorted() -> None:
    docs = {"z2": T2, "b": T, "z1": T2, "a": T, "c": T}
    assert find_duplicates(docs) == [
        DuplicateCluster(ids=("a", "b", "c"), representative="a", min_similarity=1.0),
        DuplicateCluster(ids=("z1", "z2"), representative="z1", min_similarity=1.0),
    ]


def test_find_duplicates_ignores_case_and_punctuation() -> None:
    docs = {"a": T, "b": "THE quick, brown fox; jumps over the lazy dog!!"}
    assert find_duplicates(docs) == [DuplicateCluster(("a", "b"), "a", 1.0)]


def test_find_duplicates_empty_input() -> None:
    assert find_duplicates({}) == []
    assert find_duplicates({"a": "", "b": "!!!"}) == []


def test_find_duplicates_near_duplicate_minhash() -> None:
    base = words("word", 200)
    near = base.replace("word100", "changed")
    result = find_duplicates({"a": base, "b": near, "c": words("other", 200)})
    assert len(result) == 1
    assert result[0].ids == ("a", "b")
    assert result[0].representative == "a"
    assert 0.8 <= result[0].min_similarity <= 1.0


def test_find_duplicates_threshold_controls_verification() -> None:
    docs = {"a": words("word", 200), "b": spread_variant()}
    loose = find_duplicates(docs, threshold=0.3)
    assert len(loose) == 1
    assert 0.3 <= loose[0].min_similarity < 0.9
    assert find_duplicates(docs) == []
    assert find_duplicates(docs, threshold=1.0) == []
    assert find_duplicates({"a": T, "b": T}, threshold=1.0) == [
        DuplicateCluster(("a", "b"), "a", 1.0)
    ]


def test_find_duplicates_seed_is_accepted() -> None:
    assert find_duplicates({"a": T, "b": T}, seed=99) == [DuplicateCluster(("a", "b"), "a", 1.0)]


def test_find_duplicates_simhash_identical_documents() -> None:
    docs = {"b": T, "a": T, "c": T2}
    expected = [DuplicateCluster(("a", "b"), "a", 1.0)]
    assert find_duplicates(docs, method="simhash", k=2) == expected
    assert find_duplicates(docs, method="simhash", k=2, max_hamming=0) == expected


def test_find_duplicates_simhash_unrelated_with_zero_distance_budget() -> None:
    assert find_duplicates({"a": T, "b": T2}, method="simhash", k=2, max_hamming=0) == []


def test_find_duplicates_simhash_similarity_is_one_minus_hamming_over_bits() -> None:
    left = simhash(sorted(shingles(T, k=2)))
    right = simhash(sorted(shingles(T2, k=2)))
    expected = 1 - (left ^ right).bit_count() / 64
    result = find_duplicates({"a": T, "b": T2}, method="simhash", k=2, max_hamming=63)
    assert result == [DuplicateCluster(("a", "b"), "a", expected)]


def simhash_docs() -> dict[str, str]:
    docs: dict[str, str] = {}
    base = [f"t{j}" for j in range(40)]
    for i in range(10):
        tokens = list(base)
        for j in range(i * 3):
            tokens[j] = f"r{i}x{j}"
        docs[f"d{i}"] = " ".join(tokens)
    docs["u0"] = words("u", 40)
    return docs


def brute_force_groups(docs: dict[str, str], max_hamming: int) -> set[frozenset[str]]:
    prints = {doc_id: simhash(sorted(shingles(text, k=2))) for doc_id, text in docs.items()}
    parent = {doc_id: doc_id for doc_id in docs}

    def find(item: str) -> str:
        while parent[item] != item:
            item = parent[item]
        return item

    ids = sorted(docs)
    for position, first in enumerate(ids):
        for second in ids[position + 1 :]:
            if (prints[first] ^ prints[second]).bit_count() <= max_hamming:
                parent[find(second)] = find(first)
    groups: dict[str, set[str]] = {}
    for doc_id in ids:
        groups.setdefault(find(doc_id), set()).add(doc_id)
    return {frozenset(members) for members in groups.values() if len(members) > 1}


@pytest.mark.parametrize("max_hamming", [0, 3, 10, 24, 40, 63])
def test_find_duplicates_simhash_blocks_match_brute_force(max_hamming: int) -> None:
    docs = simhash_docs()
    result = find_duplicates(docs, method="simhash", k=2, max_hamming=max_hamming)
    assert {frozenset(cluster.ids) for cluster in result} == brute_force_groups(docs, max_hamming)


def test_find_duplicates_logs_counts_without_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="near_dup_detector.dedup"):
        find_duplicates({"a": T, "b": T})
    assert caplog.records
    assert all("quick" not in record.getMessage() for record in caplog.records)


def test_find_duplicates_invalid_arguments() -> None:
    raises_code("invalid_argument", lambda: find_duplicates(["a"]))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: find_duplicates({}, threshold=0))
    raises_code("invalid_argument", lambda: find_duplicates({}, threshold=1.5))
    raises_code("invalid_argument", lambda: find_duplicates({}, threshold=float("nan")))
    raises_code("invalid_argument", lambda: find_duplicates({}, threshold=True))
    raises_code("invalid_argument", lambda: find_duplicates({}, threshold="0.5"))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: find_duplicates({}, method="x"))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: find_duplicates({}, k=0))
    raises_code("invalid_argument", lambda: find_duplicates({}, seed="1"))  # type: ignore[arg-type]
    raises_code("invalid_argument", lambda: find_duplicates({}, max_hamming=-1))
    raises_code("invalid_argument", lambda: find_duplicates({}, max_hamming=64))


def test_find_duplicates_invalid_documents() -> None:
    raises_code("invalid_argument", lambda: find_duplicates({"a": 5}))  # type: ignore[dict-item]
    raises_code("invalid_argument", lambda: find_duplicates({"": T}))
    raises_code("invalid_argument", lambda: find_duplicates({5: T}))  # type: ignore[dict-item]
    raises_code("input_too_large", lambda: find_duplicates({"x" * 1025: T}))


def test_find_duplicates_size_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    raises_code("input_too_large", lambda: find_duplicates({"a": "x" * 1_000_001}))
    monkeypatch.setattr(dedup_module, "MAX_DOCUMENTS", 2)
    raises_code("input_too_large", lambda: find_duplicates({"a": "x", "b": "y", "c": "z"}))


def test_choose_banding() -> None:
    choose = dedup_module._choose_banding
    assert choose(128, 0.8) == (16, 8)
    assert choose(128, 0.5) == (32, 4)
    assert choose(128, 1.0) == (1, 128)
    assert choose(128, 0.005) == (128, 1)
