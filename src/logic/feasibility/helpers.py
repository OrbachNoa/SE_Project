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


def partition_slots_by_window(slots: Iterable[Slot], k: int) -> List[List[Slot]]:
    """
    Split slots into independent exam-window groups for a minimum gap of k days.

    Two exams can only break a k-day gap if their candidate-date ranges are less
    than k days apart. Slots whose ranges are k days or more apart (for example a
    FALL exam period and a SPRING one, months later) can never constrain each
    other, so they belong to separate windows and must be checked on their own.

    This matters for the feasibility bound: a spare date in a far-away exam
    period must not be counted as capacity that hides a real shortage in another
    period. Grouping is by whole slot ranges (not by individual dates), so a
    single excluded day inside one period never splits that period, and every
    slot lands in exactly one window.

    Each returned list is one window's slots, in no particular order.
    """

    # Pair each slot with its candidate-date range; skip slots with no dates.
    ranged = [
        (min(slot.candidateDates), max(slot.candidateDates), slot)
        for slot in slots
        if slot.candidateDates
    ]
    if not ranged:
        return []

    # Sort by range start, so a single left-to-right sweep can find the gaps.
    ranged.sort(key=lambda item: item[0])

    windows: List[List[Slot]] = []
    current: List[Slot] = [ranged[0][2]]
    # Latest end date seen in the current window, so the next gap is measured
    # against the whole window and not just the previous slot.
    running_max = ranged[0][1]

    for lo, hi, slot in ranged[1:]:
        # A gap of k days or more from every slot so far starts a new window.
        if (lo - running_max).days >= k:
            windows.append(current)
            current = [slot]
            running_max = hi
        else:
            current.append(slot)
            if hi > running_max:
                running_max = hi

    windows.append(current)
    return windows


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