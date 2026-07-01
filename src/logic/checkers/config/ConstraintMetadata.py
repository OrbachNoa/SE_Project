from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintMeta:
    """Shared metadata for one optional scheduling constraint."""

    field_name: str
    label: str
    description: str
    unit: str
    min_k: int
    max_k: int
    default_k: int


CONSTRAINTS: tuple[ConstraintMeta, ...] = (
    ConstraintMeta(
        field_name="min_gap_obligatory",
        label="Min. gap - obligatory exams",
        description="Minimum calendar days between two mandatory exams in the same program-year.",
        unit="days",
        min_k=1,
        max_k=30,
        default_k=3,
    ),
    ConstraintMeta(
        field_name="min_gap_any",
        label="Min. gap - all exams",
        description="Minimum calendar days between any two exams (mandatory or elective) in the same program-year.",
        unit="days",
        min_k=1,
        max_k=30,
        default_k=2,
    ),
    ConstraintMeta(
        field_name="elective_conflict_cap",
        label="Elective clash cap",
        description="Maximum same-day pair-conflicts between elective exams in the same program.",
        unit="conflicts",
        min_k=0,
        max_k=10,
        default_k=2,
    ),
    ConstraintMeta(
        field_name="exam_span",
        label="Exam period span",
        description="Minimum days between the first and last mandatory exam in a program-year-moed group.",
        unit="days",
        min_k=1,
        max_k=60,
        default_k=7,
    ),
    ConstraintMeta(
        field_name="max_exams_per_day",
        label="Max exams per day",
        description="Maximum total exams allowed on any single day.",
        unit="exams / day",
        min_k=1,
        max_k=10,
        default_k=3,
    ),
)
