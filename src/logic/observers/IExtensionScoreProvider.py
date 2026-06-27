"""Optional seam for attaching extra, non-core scores to a found schedule.

The scheduling engine itself has no opinion on clustering or any other
extension feature set. QueueScheduleObserver depends only on this protocol,
not on any concrete feature computer, so the core engine can run with
clustering disabled, broken, or removed entirely.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IExtensionScoreProvider(Protocol):
    def compute(self, dto) -> dict:
        """Return extra {feature_id: value} scores for one schedule DTO."""
        ...

    def feature_ids(self) -> list:
        """Return every feature id this provider can produce."""
        ...


class NullExtensionScoreProvider:
    """Default provider: contributes no extra scores."""

    def compute(self, dto) -> dict:
        return {}

    def feature_ids(self) -> list:
        return []
