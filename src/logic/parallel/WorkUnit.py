"""One unit of work for the dynamic work-stealing scheduler.

Placement note: this lives in the logic layer (not infrastructure) because it
is a pure domain-search value object with no concurrency dependencies. The
SearchSpacePartitioner (logic) produces it and the queue/runner (infrastructure)
carry it, so keeping it in logic lets infrastructure depend on logic - never the
other way around - which respects the Clean Architecture dependency rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass(frozen=True)
class WorkUnit:
    """A single search cube: the seed dates for the leading slots.

    seed_dates[i] is the chosen date for slots[i] (the partitioner assigns slots
    in fixed leading-index order, so the alignment is by position). The resume
    start index is simply len(seed_dates); it is not stored separately. The unit
    deliberately carries only dates - no Course or ExamAssignment - so it stays
    tiny on the queue and is reconstructed against the worker's own slots.
    """

    seed_dates: List[date]
