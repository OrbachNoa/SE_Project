"""A small search task that a worker process can take from the work queue.

A WorkUnit stores only the dates that were already chosen for the first slots.
The worker later rebuilds the real ExamAssignment objects from its own slots.
This keeps the queue messages small and avoids passing heavy objects between processes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Tuple


@dataclass(frozen=True)
class WorkUnit:
    """Fixed starting dates for one part of the scheduling search."""

    # seed_dates[i] is the fixed date for slots[i].
    # The worker continues the search from len(seed_dates).
    seed_dates: Tuple[date, ...]
