from __future__ import annotations


class ClusterTranslationError(Exception):
    """Raised when a configured LLM fails/times out translating a cluster request.

    Deliberately not raised when no LLM is configured at all (the heuristic
    parser handles that case) — only when the LLM was expected to answer and
    didn't, so the caller must not silently fall back and hide the failure.
    """

    def __init__(self, message: str = "LLM clustering request failed") -> None:
        super().__init__(message)
