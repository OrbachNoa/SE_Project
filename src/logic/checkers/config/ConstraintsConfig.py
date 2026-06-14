from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ConstraintsConfig:
    """Toggle and threshold (k) for each Phase-3 threshold constraint.

    A value of None disables the constraint. An integer is its k threshold.
    Plain immutable data only, so it can be pickled and sent to each worker
    process unchanged.
    """
    min_gap_obligatory: Optional[int] = None     # 2.1
    min_gap_any: Optional[int] = None            # 2.2
    elective_conflict_cap: Optional[int] = None  # 2.3
    exam_span: Optional[int] = None              # 2.4
    max_exams_per_day: Optional[int] = None      # 2.5