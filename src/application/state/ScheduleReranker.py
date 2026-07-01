"""Runtime re-ranking of schedules by the user's chosen sort order (SCRUM-223).

The sort scores were computed once, at generation time, and stored on each
ScheduleDTO.scores. Re-ranking never recomputes them — it just orders the
schedules by those stored numbers, in the priority the user picked.

Scope (Option A, window-only): this orders the schedules currently in memory.
For the disk-backed Hybrid state that means the current page, not the whole
result set. A future change can push the sort down to the repository for a
global ordering without touching the comparators or the score format.

Contract with the sort-config UI (SCRUM-222): it passes a list of criterion-id
strings in priority order, e.g. ["MANDATORY_SPAN", "MAX_EXAMS_PER_DAY"]. The
first id is the primary sort, the next breaks ties, and so on. Every score
follows the higher-is-better convention, so every level sorts descending.
"""
from __future__ import annotations

from typing import List

from src.application.dto.ScheduleDTO import ScheduleDTO

# Used when a schedule has no score for a requested criterion (for example an
# older schedule generated without a scorer). Such schedules sort to the bottom
# rather than crashing the sort.
_MISSING_SCORE = float("-inf")


def sort_key(schedule: ScheduleDTO, priority: List[str]) -> tuple:
    """Build the sort key for one schedule, following the priority order.

    Returns a tuple of the schedule's scores in priority order. Because higher
    is better for every criterion, the caller sorts with reverse=True so the
    whole tuple compares descending, primary criterion first.
    """
    scores = schedule.scores or {}
    return tuple(scores.get(criterion_id, _MISSING_SCORE) for criterion_id in priority)


def rerank(schedules: List[ScheduleDTO], priority: List[str]) -> List[ScheduleDTO]:
    """Return the schedules ordered by the given priority of criterion ids.

    An empty priority list means "no sort": the schedules are returned in their
    existing order, unchanged. The sort is stable, so schedules that tie on
    every requested criterion keep their original relative order.
    """
    if not priority:
        return list(schedules)
    return sorted(schedules, key=lambda s: sort_key(s, priority), reverse=True)