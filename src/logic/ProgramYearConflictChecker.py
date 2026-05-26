from .IConflictChecker import IConflictChecker
from ..models.enums import Requirement


class ProgramYearConflictChecker(IConflictChecker):
    """
    Detects scheduling conflicts between courses that share the same
    (program, year) cohort, where at least one of the courses is
    obligatory for that cohort.

    Builds a conflict graph once via precompute_conflicts(), then answers
    O(1) lookups via check(). precompute_conflicts() must be called before
    any check() - the checker fails loudly otherwise rather than silently
    degrading to a slow path.
    """

    def __init__(self):
        # Conflict graph: course_id -> set of course_ids that conflict with it.
        # None until precompute_conflicts() is called.
        self._conflict_graph = None
        # Programs the user explicitly selected. Conflicts in programs the
        # user didn't pick are irrelevant. None means "consider all programs".
        self._selected_programs = None

    def precompute_conflicts(self, courses: list, selected_programs: list = None) -> None:
        """
        Builds the conflict graph for the given courses. Must be called once
        before any check() call. Cost: O(n * avg_entries + n^2 * avg_shared_keys)
        where n = number of courses. The improvement over the previous version
        is that each course's entries dict is built ONCE, not n times.
        """
        # Store selected programs as a set, so program lookups are O(1).
        self._selected_programs = set(selected_programs) if selected_programs else None

        # Build the (program, year) -> entry dict for each course exactly once.
        # The original code rebuilt entries2 inside the inner loop, so the
        # entries-construction cost alone was O(n^2). Now it is O(n).
        all_entries = self._build_all_entries(courses)

        # Initialize an empty conflict set for each course.
        self._conflict_graph = {c.courseId: set() for c in courses}

        # Pairwise comparison - each pair examined exactly once.
        for i, c1 in enumerate(courses):
            entries1 = all_entries[c1.courseId]
            # Courses with no entries in the selected programs cannot conflict.
            if not entries1:
                continue
            for c2 in courses[i + 1:]:
                entries2 = all_entries[c2.courseId]
                if not entries2:
                    continue
                # Walk shared (program, year) keys. Stop at the first conflict
                # since the graph only records whether the pair conflicts at
                # all, not how many shared keys cause it.
                for key in entries1.keys() & entries2.keys():
                    if (entries1[key].requirement == Requirement.OBLIGATORY or
                            entries2[key].requirement == Requirement.OBLIGATORY):
                        self._conflict_graph[c1.courseId].add(c2.courseId)
                        self._conflict_graph[c2.courseId].add(c1.courseId)
                        break

    def _build_all_entries(self, courses: list) -> dict:
        """
        Returns a dict course_id -> {(program_id, year): entry}, with entries
        already filtered to the selected programs. Computed once and reused
        for every pair comparison in precompute_conflicts().
        """
        all_entries = {}
        for c in courses:
            all_entries[c.courseId] = {
                (e.programId, e.year): e for e in c.programEntries
                if not self._selected_programs or e.programId in self._selected_programs
            }
        return all_entries

    def check(self, assignment, schedule) -> bool:
        """
        Returns True when scheduling `assignment` creates a conflict with a
        course already in `schedule`. O(1) lookup via the precomputed graph.

        Raises RuntimeError if precompute_conflicts() has not been called.
        The previous fallback path silently degraded to O(n * k) per call -
        a forgotten setup turned into a performance regression invisible
        to the caller. Failing loudly is safer.
        """
        if self._conflict_graph is None:
            raise RuntimeError(
                "ProgramYearConflictChecker.precompute_conflicts() must be "
                "called before check(). The caller (typically main.py or a "
                "test fixture) is responsible for setup."
            )

        new_id = assignment.course.courseId
        # The set of course_ids that conflict with the new course.
        conflicts = self._conflict_graph.get(new_id, set())
        # Early exit: course has no conflicts at all, so no schedule state
        # can produce one.
        if not conflicts:
            return False

        # Courses already scheduled on the same date.
        courses_on_date = schedule._date_to_course_ids.get(assignment.date)
        if not courses_on_date:
            return False

        # Conflict iff any course on this date is in the conflict set.
        # set.isdisjoint is O(min(|a|, |b|)) - O(1) in practice for small sets.
        return not courses_on_date.isdisjoint(conflicts)