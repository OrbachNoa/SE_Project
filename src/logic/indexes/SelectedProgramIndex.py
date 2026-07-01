from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from src.models.Enums import Requirement


class SelectedProgramIndex:
    """
    Stores selected-program lookups for one scheduling run.

    Course.programEntries stays unchanged. This object only keeps filtered
    views that checkers, rules and metrics can reuse.
    """

    def __init__(self, courses: list, selected_programs: Optional[list] = None, slots: Optional[list] = None):
        # Store selected programs once, so every lookup can reuse the same filter.
        self.selected_programs = frozenset(selected_programs or [])
        # Keep a set version for older code paths that expect selected_set.
        self.selected_set = set(self.selected_programs) if self.selected_programs else None

        self._entries_by_course: Dict[str, Tuple[object, ...]] = {}
        self._entries_by_course_semester: Dict[Tuple[str, object], Tuple[object, ...]] = {}
        self._slots = list(slots or [])
        self._entries_by_slot: Dict[object, Tuple[object, ...]] = {}
        self._slot_group_cache: Dict[Tuple[str, Optional[Requirement]], dict] = {}

        for course in courses:
            entries = tuple(
                entry for entry in (course.programEntries or [])
                if self.includes(entry.programId)
            )
            self._entries_by_course[course.courseId] = entries

            by_semester: Dict[object, List[object]] = defaultdict(list)
            for entry in entries:
                by_semester[entry.semester].append(entry)
            for semester, semester_entries in by_semester.items():
                self._entries_by_course_semester[(course.courseId, semester)] = tuple(semester_entries)

        for slot in self._slots:
            self._entries_by_slot[slot] = self.entries_for_course_semester(
                slot.course.courseId,
                slot.semester,
            )

    @classmethod
    def from_slots(cls, slots: Iterable[object], selected_programs: Optional[list] = None) -> "SelectedProgramIndex":
        """Build an index from the unique courses referenced by the slots."""

        # Keep course order stable by first appearance in the slot list.
        courses = []
        seen = set()
        slot_list = list(slots)
        for slot in slot_list:
            course_id = slot.course.courseId
            if course_id in seen:
                continue
            seen.add(course_id)
            courses.append(slot.course)
        return cls(courses, selected_programs, slot_list)

    def includes(self, program_id: str) -> bool:
        """Return True when this program belongs to the current run."""

        return not self.selected_programs or program_id in self.selected_programs

    def entries_for_course(self, course_id: str) -> Tuple[object, ...]:
        """Return selected entries for the course."""

        return self._entries_by_course.get(course_id, ())

    def entries_for_course_semester(self, course_id: str, semester) -> Tuple[object, ...]:
        """Return selected entries for the course in one semester."""

        return self._entries_by_course_semester.get((course_id, semester), ())

    def entries_for_slot(self, slot) -> Tuple[object, ...]:
        """Return selected entries that match the slot semester."""

        return self._entries_by_slot.get(
            slot,
            self.entries_for_course_semester(slot.course.courseId, slot.semester),
        )

    def has_entries_for_course(self, course_id: str) -> bool:
        """Return True if the course has at least one selected entry."""

        return bool(self.entries_for_course(course_id))

    def slots_by_program_year(
        self,
        slots: Optional[Iterable[object]] = None,
        requirement: Optional[Requirement] = None,
    ) -> Dict[Tuple[str, int], Set[object]]:
        """Group slots by program and year using course-level entries."""

        return self._group_slots("program_year", slots, requirement)

    def slots_by_program(
        self,
        slots: Optional[Iterable[object]] = None,
        requirement: Optional[Requirement] = None,
    ) -> Dict[str, Set[object]]:
        """Group slots by program using course-level entries."""

        return self._group_slots("program", slots, requirement)

    def slots_by_program_year_semester_moed(
        self,
        slots: Optional[Iterable[object]] = None,
        requirement: Optional[Requirement] = None,
    ) -> Dict[Tuple[str, int, object, object], Set[object]]:
        """Group slots by program, year, semester and moed using slot entries."""

        return self._group_slots("program_year_semester_moed", slots, requirement)

    def _group_slots(
        self,
        group_type: str,
        slots: Optional[Iterable[object]],
        requirement: Optional[Requirement],
    ) -> dict:
        slot_list = self._slots if slots is None else list(slots)
        cache_key = (group_type, requirement) if slots is None else None
        if cache_key is not None and cache_key in self._slot_group_cache:
            return self._slot_group_cache[cache_key]

        groups = defaultdict(set)

        for slot in slot_list:
            if group_type == "program_year_semester_moed":
                entries = self.entries_for_slot(slot)
            else:
                entries = self.entries_for_course(slot.course.courseId)

            for entry in entries:
                if requirement is not None and entry.requirement is not requirement:
                    continue

                if group_type == "program":
                    key = entry.programId
                elif group_type == "program_year":
                    key = (entry.programId, entry.year)
                else:
                    key = (entry.programId, entry.year, slot.semester, slot.moed)
                groups[key].add(slot)

        result = dict(groups)
        if cache_key is not None:
            self._slot_group_cache[cache_key] = result
        return result
