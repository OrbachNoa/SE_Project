from .IConflictChecker import IConflictChecker
from ..models.enums import Requirement

class ProgramYearConflictChecker(IConflictChecker):
    """
    Precomputes conflicts between courses sharing the same program and year,
    allowing for O(1) conflict validation during the backtracking search.
    """
    def __init__(self):
        self._conflict_graph = None
        # Store selected programs, so checks ignore unrelated programs.
        self._selected_programs = None

    def precompute_conflicts(self, courses: list, selected_programs: list = None) -> None:
        # Store selected programs as a set, so program lookups are fast.
        self._selected_programs = set(selected_programs) if selected_programs else None
        # Initialize an empty dict for each course, for mapping direct conflicts.
        self._conflict_graph = {c.courseId: set() for c in courses}

        for i, c1 in enumerate(courses):
            # Keep only selected program entries, so unrelated programs do not conflict.
            entries1 = {
                (e.programId, e.year): e for e in c1.programEntries
                if not self._selected_programs or e.programId in self._selected_programs
            }
            # Compare with remaining courses in the list.
            for c2 in courses[i + 1:]:
                entries2 = {
                    (e.programId, e.year): e for e in c2.programEntries
                    if not self._selected_programs or e.programId in self._selected_programs
                }
                # Find Intersecting keys to find cohorts (same program and year) enrolled in both courses.
                for key in entries1.keys() & entries2.keys():
                    # Flag a conflict if one of the courses is mandatory.
                    if (entries1[key].requirement == Requirement.OBLIGATORY or
                            entries2[key].requirement == Requirement.OBLIGATORY):
                        # Build a bidirectional edge in the graph, so either course can detect the conflict later.
                        self._conflict_graph[c1.courseId].add(c2.courseId)
                        self._conflict_graph[c2.courseId].add(c1.courseId)
                        break

    def check(self, assignment, schedule) -> bool:
        new_date   = assignment.date
        new_course = assignment.course
        new_id     = new_course.courseId

        # Use the precomputed conflict graph if available.
        if self._conflict_graph is not None:
            conflicts = self._conflict_graph.get(new_id, set())
            # Return early if this course has no conflicts with other courses.
            if not conflicts:
                return False

            # Extract courses already scheduled on current date.
            courses_on_date = schedule._date_to_course_ids.get(new_date)
            if courses_on_date:
                # Check for overlaps by set intersection.
                return not courses_on_date.isdisjoint(conflicts)
            return False

        # Check conflicts without the graph, so the checker still works as a fallback.
        for existing in schedule.assignments:
            if existing.date != new_date:
                continue

            # Filter entries here too, so fallback behavior matches the precomputed check.
            new_entries = {
                (e.programId, e.year): e for e in new_course.programEntries
                if not self._selected_programs or e.programId in self._selected_programs
            }
            existing_entries = {
                (e.programId, e.year): e for e in existing.course.programEntries
                if not self._selected_programs or e.programId in self._selected_programs
            }

            for key in new_entries.keys() & existing_entries.keys():
                if (new_entries[key].requirement == Requirement.OBLIGATORY or
                        existing_entries[key].requirement == Requirement.OBLIGATORY):
                    return True
        return False
