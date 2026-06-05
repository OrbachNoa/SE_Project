from .IConflictChecker import IConflictChecker
from src.models.Enums import Requirement


class ProgramYearConflictChecker(IConflictChecker):
    """Checks course conflicts for the same program and year."""

    def __init__(self):
        # Keep the conflict graph here, so checks can be fast later.
        self._conflict_graph = None
        # Keep selected programs here, so unrelated programs can be ignored.
        self._selected_programs = None

    def precompute_conflicts(self, courses: list, selected_programs: list = None) -> None:
        """Builds the conflict graph before scheduling starts."""
        # Store selected programs as a set, so program lookups are O(1).
        self._selected_programs = set(selected_programs) if selected_programs else None

        # Build each course entry map once, so pair checks do less work.
        all_entries = self._build_all_entries(courses)

        # Initialize an empty conflict set for each course.
        self._conflict_graph = {c.courseId: set() for c in courses}

        # Compare each course pair once, so duplicate checks are avoided.
        for i, c1 in enumerate(courses):
            entries1 = all_entries[c1.courseId]
            # Courses with no entries in the selected programs cannot conflict.
            if not entries1:
                continue
            for c2 in courses[i + 1:]:
                entries2 = all_entries[c2.courseId]
                if not entries2:
                    continue
                # Check shared program-year keys, so only real cohort overlaps count.
                for key in entries1.keys() & entries2.keys():
                    if (entries1[key].requirement == Requirement.OBLIGATORY or
                            entries2[key].requirement == Requirement.OBLIGATORY):
                        self._conflict_graph[c1.courseId].add(c2.courseId)
                        self._conflict_graph[c2.courseId].add(c1.courseId)
                        break

    def _build_all_entries(self, courses: list) -> dict:
        """Builds course entry maps, so conflict checks can reuse them."""
        all_entries = {}
        for c in courses:
            all_entries[c.courseId] = {
                (e.programId, e.year): e for e in c.programEntries
                if not self._selected_programs or e.programId in self._selected_programs
            }
        return all_entries

    def check(self, assignment, schedule) -> bool:
        """Returns True when this assignment conflicts with the schedule."""
        if self._conflict_graph is None:
            raise RuntimeError(
                "ProgramYearConflictChecker.precompute_conflicts() must be "
                "called before check(). The caller (typically main.py or a "
                "test fixture) is responsible for setup."
            )

        new_id = assignment.course.courseId
        # The set of course_ids that conflict with the new course.
        conflicts = self._conflict_graph.get(new_id, set())
        # Stop early when this course has no known conflicts.
        if not conflicts:
            return False

        # Courses already scheduled on the same date.
        courses_on_date = schedule._date_to_course_ids.get(assignment.date)
        if not courses_on_date:
            return False

        # Check date courses against conflicts, so same-day clashes are detected.
        return not courses_on_date.isdisjoint(conflicts)
