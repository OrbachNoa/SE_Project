from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

from src.logic.SlotBuilder import Slot


def all_dates(slots: Iterable[Slot]) -> List[date]:
    return sorted({candidate for slot in slots for candidate in slot.candidateDates})


def slots_by_domain(slots: Iterable[Slot]) -> Dict[frozenset, List[Slot]]:
    groups: Dict[frozenset, List[Slot]] = defaultdict(list)
    for slot in slots:
        domain = frozenset(slot.candidateDates)
        if domain:
            groups[domain].append(slot)
    return groups


def first_after(candidates: List[date], previous: Optional[date]) -> Optional[date]:
    for candidate in sorted(candidates):
        if previous is None or candidate > previous:
            return candidate
    return None


def max_spaced_count(candidates: List[date], k: int) -> int:
    count = 0
    previous: Optional[date] = None
    for candidate in sorted(set(candidates)):
        if previous is None or (candidate - previous).days >= k:
            count += 1
            previous = candidate
    return count


def max_electives_per_day(k: int) -> int:
    count = 0
    while (count + 1) * count // 2 <= k:
        count += 1
    return count


def enum_name(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
