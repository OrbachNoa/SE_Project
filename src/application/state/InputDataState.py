"""InputDataState - runtime state for the user's loaded input data.

The input half of the application state: holds the courses and
exam periods the user has loaded. In addition, it owns the
bridge to the on-disk cache and translate between the live
domain objects and the persistence-only DataCache. This is
the place where the domain<->cache shape conversion happens.
"""
from __future__ import annotations

from datetime import date
from typing import List, TYPE_CHECKING

# A guard for avoiding circular imports between this class and the vm class used
# in calendar editor, which needs to call back into this state to apply edits.
if TYPE_CHECKING:
    from viewmodels.PeriodEditViewModel import PeriodEditViewModel

from src.models.Course import Course, ProgramEntry
from src.models.ExamPeriod import ExamPeriod
from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.infrastructure.cache.DataCache import DataCache, CourseDict, PeriodDict


class InputDataState:
    """Holds loaded courses and exam periods, plus the on-disk cache bridge."""

    def __init__(self) -> None:
        # The loaded courses from the user's input.
        self._courses: List[Course] = []
        # The loaded exam periods from the user's input.
        self._periods: List[ExamPeriod] = []
        # The program IDs user selected before launching generation.
        self._selected_program_ids: List[str] = []

    # --- accessors / mutators (UML) ----------------------------------------

    def set_selected_programs(self, program_ids: List[str]) -> None:
        """Store a copy of the program IDs chosen by the user for the current run.

        A copy is stored (rather than the original list) so that external mutations
        of the caller's list cannot silently corrupt the stored state. These IDs are
        needed later — after the scheduler has finished — when the display layer maps
        each ScheduleDTO to a view model and must know which programs were in scope
        for the generation run.
        """
        self._selected_program_ids = list(program_ids)

    def get_selected_programs(self) -> List[str]:
        """Return a copy of the stored program IDs for the current generation run.

        A copy is returned so callers cannot accidentally mutate the internal list.
        Returns an empty list if set_selected_programs has never been called.
        """
        return list(self._selected_program_ids)

    def replace_courses(self, courses: List[Course]) -> None:
        """Replace all loaded courses (REPLACE-mode import)."""
        self._courses = list(courses)

    def replace_periods(self, periods: List[ExamPeriod]) -> None:
        """Replace all loaded exam periods (REPLACE-mode import)."""
        self._periods = list(periods)

    def get_courses(self) -> List[Course]:
        """Return the loaded courses."""
        return self._courses

    def get_periods(self) -> List[ExamPeriod]:
        """Return the loaded exam periods."""
        return self._periods
    
    def apply_period_edits(self, edited_vms: List["PeriodEditViewModel"]) -> None:
        """Apply edited periods from the calendar editor onto the stored periods."""
        # Index incoming edits by (semester, moed) for efficient lookup
        edits_by_key = {(vm.semester, vm.moed): vm for vm in edited_vms}

        rebuilt: List[ExamPeriod] = []
        for period in self._periods:
            key = (period.semester.value, period.moed.value)
            vm = edits_by_key.get(key)
            if vm is None:
                # No edit for this period; keep it as-is
                rebuilt.append(period)
                continue
            # Rebuild from the edited values: ISO strings -> date, str -> enum.
            # A new ExamPeriod re-validates the range and recomputes availableDates.
            rebuilt.append(
                ExamPeriod(
                    semester=Semester(vm.semester),
                    moed=Moed(vm.moed),
                    start_date=date.fromisoformat(vm.start_date),
                    end_date=date.fromisoformat(vm.end_date),
                    excluded_dates=[date.fromisoformat(d) for d in vm.excluded_dates],
                )
            )

        self._periods = rebuilt

    # --- cache bridge (lead's two extra methods) ---------------------------

    def to_cache(self) -> DataCache:
        """Serialize current courses/periods into a DataCache (domain -> dicts).

        source_hashes/saved_at/schema_version are left to DataCache's defaults;
        the FileImportService fills source_hashes when it knows the file paths.
        """
        course_dicts: List[CourseDict] = [
            {
                "courseId": c.courseId,
                "name": c.name,
                "instructor": c.instructor,
                "evaluation": c.evaluation.value,
                "programEntries": [
                    {
                        "programId": e.programId,
                        "year": e.year,
                        "semester": e.semester.value,
                        "requirement": e.requirement.value,
                    }
                    for e in c.programEntries
                ],
            }
            for c in self._courses
        ]

        # The exam periods' excludedDates are sorted in the cache for readability and consistency, even though the order doesn't matter in the domain objects.
        period_dicts: List[PeriodDict] = [
            {
                "semester": p.semester.value,
                "moed": p.moed.value,
                "startDate": p.startDate.isoformat(),
                "endDate": p.endDate.isoformat(),
                "excludedDates": sorted(d.isoformat() for d in p.excludedDates),
            }
            for p in self._periods
        ]

        return DataCache(courses=course_dicts, periods=period_dicts)

    def load_cache(self, cache: DataCache) -> None:
        """Rebuild courses/periods from a DataCache (dicts -> domain objects).

        Replaces current state. Inverse of to_cache(): enum values become enum
        members and ISO strings become date objects.
        """
        rebuilt_courses: List[Course] = []
        for cd in cache.courses:
            entries = [
                ProgramEntry(
                    program_id=ed["programId"],
                    year=ed["year"],
                    semester=Semester(ed["semester"]),
                    requirement=Requirement(ed["requirement"]),
                )
                for ed in cd.get("programEntries", [])
            ]
            rebuilt_courses.append(
                Course(
                    course_id=cd["courseId"],
                    name=cd["name"],
                    instructor=cd["instructor"],
                    evaluation=EvalType(cd["evaluation"]),
                    program_entries=entries,
                )
            )

        rebuilt_periods: List[ExamPeriod] = []
        for pd in cache.periods:
            rebuilt_periods.append(
                ExamPeriod(
                    semester=Semester(pd["semester"]),
                    moed=Moed(pd["moed"]),
                    start_date=date.fromisoformat(pd["startDate"]),
                    end_date=date.fromisoformat(pd["endDate"]),
                    excluded_dates=[date.fromisoformat(d) for d in pd.get("excludedDates", [])],
                )
            )

        self._courses = rebuilt_courses
        self._periods = rebuilt_periods
