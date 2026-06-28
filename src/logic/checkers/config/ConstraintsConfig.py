from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.logic.checkers.config.ConstraintMetadata import CONSTRAINTS


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

    def validate(self) -> None:
        """Raise ValueError if any enabled rule has an out-of-range k value.

        None always means "disabled" and is always valid. Every rule except
        elective_conflict_cap must be a positive integer when enabled;
        elective_conflict_cap may be 0 (a program may not have any same-day
        elective pair). Checkers otherwise silently disable on k <= 0, which
        hides a misconfiguration instead of rejecting it.
        """
        invalid = [
            meta.field_name
            for meta in CONSTRAINTS
            if (value := getattr(self, meta.field_name)) is not None
            and value < meta.min_k
        ]
        if invalid:
            raise ValueError(
                f"Invalid constraint value(s): {', '.join(invalid)}. "
                "Must be a positive integer (elective_conflict_cap may be 0)."
            )
