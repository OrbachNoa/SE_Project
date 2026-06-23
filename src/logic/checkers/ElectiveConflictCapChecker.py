from __future__ import annotations
from collections import Counter, defaultdict
from typing import Dict, List, Set

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, min_pair_conflicts, slots_by_domain
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """Limits elective exam pair-conflicts per program to at most k, counted
    across the whole schedule (not per day).

    Years are intentionally ignored for this rule: every elective course in the
    same program participates in the same conflict count. Same-day pairs are
    what count: a same-day group of n elective exams contributes
    n * (n - 1) / 2 pair-conflicts, and the cap applies to the sum of that
    quantity over every day in the schedule.
    """

    def __init__(self, k: int):
        self._k = k
        # programId -> set of elective courseIds for O(1) membership test.
        self._program_elective_sets: Dict[str, Set[str]] = {}
        # courseId -> programs where this course is elective.
        self._course_programs: Dict[str, List[str]] = {}
        # Cache of the last computed per-program/per-date elective counts,
        # tagged with the ExamSchedule instance and its version at the time it
        # was built. check() is called from the hot forward-check loop for
        # every candidate date of every domain while the committed schedule
        # does not change at all between those calls, so recomputing the
        # per-date counts from scratch on every call would rescan the
        # program's electives once per candidate date instead of once per
        # actual backtracking step. The cache makes that rescan happen only
        # when the schedule actually changes (an add or a pop).
        self._index_cache: Dict[int, tuple] = {}

    def _program_date_counts(self, schedule) -> Dict[str, Counter]:
        cached = self._index_cache.get(id(schedule))
        if cached is not None and cached[0] is schedule and cached[1] == schedule.version:
            return cached[2]

        index: Dict[str, Counter] = {}
        for program_id, electives in self._program_elective_sets.items():
            counts: Counter = Counter()
            for course_id in electives:
                for a in schedule.assignments_for_course(course_id):
                    counts[a.date] += 1
            index[program_id] = counts
        self._index_cache = {id(schedule): (schedule, schedule.version, index)}
        return index

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        selected = set(selected_programs) if selected_programs else None
        program_elective_sets: Dict[str, Set[str]] = {}
        course_programs: Dict[str, List[str]] = {}
        for course in courses:
            for entry in course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.ELECTIVE:
                    continue
                program_elective_sets.setdefault(entry.programId, set()).add(course.courseId)
                owned = course_programs.setdefault(course.courseId, [])
                if entry.programId not in owned:
                    owned.append(entry.programId)
        self._program_elective_sets = program_elective_sets
        self._course_programs = course_programs

    def check(self, assignment, schedule) -> bool:
        programs = self._course_programs.get(assignment.course.courseId)
        if not programs:
            return False

        index = self._program_date_counts(schedule)
        for program_id in programs:
            per_date_counts = index.get(program_id)
            if not per_date_counts:
                continue
            # Total pair-conflicts already committed for this program, plus the
            # new pairs the candidate would add on its own date.
            existing_total = sum(n * (n - 1) // 2 for n in per_date_counts.values())
            new_pairs = per_date_counts.get(assignment.date, 0)
            if existing_total + new_pairs > self._k:
                return True
        return False

    def feasibility_bound(self, context) -> List[str]:
        """Preflight: can each program's elective exams be spread across their
        candidate dates without the total same-day pair-conflicts exceeding k,
        even in the best-case (most even) arrangement?
        """
        selected = context.selected_set
        by_program: Dict[str, Set] = defaultdict(set)
        for slot in context.slots:
            for entry in slot.course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is Requirement.ELECTIVE:
                    by_program[entry.programId].add(slot)

        errors = []
        for program_id, program_slots in by_program.items():
            dates = all_dates(program_slots)
            if dates and min_pair_conflicts(len(program_slots), len(dates)) > self._k:
                errors.append(
                    f"Elective conflict cap {self._k} cannot be met for program "
                    f"{program_id}: even spread as evenly as possible, "
                    f"{len(program_slots)} elective exams across {len(dates)} "
                    f"possible dates produce more than {self._k} pair-conflicts."
                )
                continue

            for domain, same_domain_slots in slots_by_domain(program_slots).items():
                if min_pair_conflicts(len(same_domain_slots), len(domain)) > self._k:
                    errors.append(
                        f"Elective conflict cap {self._k} cannot be met for program "
                        f"{program_id}: even spread as evenly as possible, "
                        f"{len(same_domain_slots)} elective exams sharing the same "
                        f"{len(domain)} possible dates produce more than {self._k} "
                        "pair-conflicts."
                    )
        return errors
