"""Behavior tests for the public API of near_dup_detector."""

from __future__ import annotations

import pytest

import near_dup_detector


def test_normalize_trims_and_lowercases() -> None:
    assert near_dup_detector.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        near_dup_detector.normalize(value)


def test_version_is_semver() -> None:
    parts = near_dup_detector.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
