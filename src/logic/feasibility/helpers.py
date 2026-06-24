from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

from src.logic.SlotBuilder import Slot


def all_dates(slots: Iterable[Slot]) -> List[date]:
    """
    Return all possible exam dates from all slots, without duplicates.

    The result is sorted, so later checks can use the dates in order.
    """

    # Build set of all candidate dates from all slots to remove duplicates.
    # Then sort it before returning.
    return sorted({candidate for slot in slots for candidate in slot.candidateDates})


def slots_by_domain(slots: Iterable[Slot]) -> Dict[frozenset, List[Slot]]:
    """
    Group slots that have the same possible exam dates.

    Domain means the set of candidate dates of the slot.
    Slots with the same domain have the exact same date options.
    """

    # Dict where key is date domain, and value is all slots with this domain.
    groups: Dict[frozenset, List[Slot]] = defaultdict(list)

    for slot in slots:
        # Convert candidate dates to frozenset so it can be used as dict key.
        domain = frozenset(slot.candidateDates)

        # Ignore empty domains, because there are no possible dates to group.
        if domain:
            groups[domain].append(slot)

    return groups


def first_after(candidates: List[date], previous: Optional[date]) -> Optional[date]:
    """
    Return the first date that comes after the previous date.

    If previous is None, return the first date from the sorted candidates.
    If no date comes after previous, return None.
    """

    # Go over the candidate dates in sorted order.
    for candidate in sorted(candidates):
        # If there is no previous date, or this candidate is after previous,
        # this is the first valid date.
        if previous is None or candidate > previous:
            return candidate

    # There is no candidate date after previous.
    return None


def max_spaced_count(candidates: List[date], k: int) -> int:
    """
    Return how many dates can be picked with at least k days between them.

    This is greedy: always take the earliest date that fits.
    For sorted dates, this gives the maximum amount of dates we can choose.
    """

    # How many dates we succeeded to choose.
    count = 0

    # Last date that we chose.
    previous: Optional[date] = None

    # Use set to remove duplicate dates, then sort the dates.
    for candidate in sorted(set(candidates)):
        # Take the date if it is the first one,
        # or if it is at least k days after the previous chosen date.
        if previous is None or (candidate - previous).days >= k:
            count += 1
            previous = candidate

    return count


def min_pair_conflicts(n: int, d: int) -> int:
    """
    Return the minimum total same-day pair-conflicts.

    n is the number of exams.
    d is the number of available dates.

    To minimize conflicts, we spread the exams as evenly as possible across the dates.
    """

    # If there are no available dates, we cant spread the exams.
    if d <= 0:
        return 0

    # q is how many exams each date gets at minimum.
    # r is how many dates get one extra exam.
    q, r = divmod(n, d)

    # r dates have q + 1 exams.
    # d - r dates have q exams.
    # For each date, number of conflict pairs is count * (count - 1) / 2.
    return r * (q + 1) * q // 2 + (d - r) * q * (q - 1) // 2


def enum_name(value) -> str:
    """
    Return the real enum value, or regular text if it is not an enum.
    """

    # If this is enum, return its value.
    # Otherwise convert it to string.
    return value.value if hasattr(value, "value") else str(value)