from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

from src.logic.SlotBuilder import Slot


def all_dates(slots: Iterable[Slot]) -> List[date]:
    """Return all possible exam dates from all slots, without duplicates."""
    return sorted({candidate for slot in slots for candidate in slot.candidateDates})


def slots_by_domain(slots: Iterable[Slot]) -> Dict[frozenset, List[Slot]]:
    """Group slots that have the same possible exam dates."""
    groups: Dict[frozenset, List[Slot]] = defaultdict(list)
    for slot in slots:
        domain = frozenset(slot.candidateDates)
        if domain:
            groups[domain].append(slot)
    return groups


def first_after(candidates: List[date], previous: Optional[date]) -> Optional[date]:
    """Return the first date that comes after the previous date."""
    for candidate in sorted(candidates):
        if previous is None or candidate > previous:
            return candidate
    return None


def max_spaced_count(candidates: List[date], k: int) -> int:
    """Return how many dates can be picked with at least k days between them."""
    count = 0
    previous: Optional[date] = None
    for candidate in sorted(set(candidates)):
        if previous is None or (candidate - previous).days >= k:
            count += 1
            previous = candidate
    return count


def min_pair_conflicts(n: int, d: int) -> int:
    """Return the minimum total same-day pair-conflicts achievable by spreading
    n exams across d available dates as evenly as possible.

    Splitting n items into d bins as evenly as possible (some bins get q+1,
    the rest get q, where q, r = divmod(n, d)) minimizes the sum of C(count, 2)
    over all bins; any less even split only adds conflicts.
    """
    if d <= 0:
        return 0
    q, r = divmod(n, d)
    return r * (q + 1) * q // 2 + (d - r) * q * (q - 1) // 2


def enum_name(value) -> str:
    """Return the real enum value, or regular text if it is not an enum."""
    return value.value if hasattr(value, "value") else str(value)
