"""Typed errors raised by the library."""

from __future__ import annotations

from typing import Literal

ErrorCode = Literal["invalid_argument", "duplicate_id", "input_too_large", "index_full"]

MAX_MESSAGE_CHARS = 200


class DedupError(ValueError):
    """Base error of the library.

    Attributes:
        code: Stable machine-readable error code.
    """

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message[:MAX_MESSAGE_CHARS])
        self.code: ErrorCode = code

    def __reduce__(self) -> tuple[type[DedupError], tuple[ErrorCode, str]]:
        return (type(self), (self.code, str(self)))
