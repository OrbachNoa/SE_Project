from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ConstraintsConfig:
    """Stores the optional scheduling rules selected by the user.

    None means the rule is turned off.
    An integer value means the rule is turned on with that k value.
    """

    # 2.1 - Minimum days between mandatory exams in the same program and year.
    min_gap_obligatory: Optional[int] = None
    # 2.2 - Minimum days between any exams in the same program and year.
    min_gap_any: Optional[int] = None
    # 2.3 - Maximum allowed elective same-day pair conflicts per program.
    elective_conflict_cap: Optional[int] = None
    # 2.4 - Minimum span between first and last mandatory exam in a cohort.
    exam_span: Optional[int] = None
    # 2.5 - Maximum number of exams allowed on the same day.
    max_exams_per_day: Optional[int] = None