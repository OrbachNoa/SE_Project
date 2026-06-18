from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Set

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, max_electives_per_day, slots_by_domain
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """Limits elective exam pair-conflicts per program to at most k.

    Years are intentionally ignored for this rule: every elective course in the
    same program participates in the same conflict count. A same-day group of n
    elective exams creates n * (n - 1) / 2 pair-conflicts.
    """

    def __init__(self, k: int):
        self._k = k
        # programId -> set of elective courseIds for O(1) membership test.
        self._program_elective_sets: Dict[str, Set[str]] = {}
        # courseId -> programs where this course is elective.
        self._course_programs: Dict[str, List[str]] = {}

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

        # Reuse the O(1) date index; only the new date can create a new clash.
        ids_on_date = schedule.course_ids_on_date(assignment.date)

        for program_id in programs:
            electives_in_program = self._program_elective_sets[program_id]
            count = 1  # count the assignment being placed
            for other_id in ids_on_date:
                if other_id in electives_in_program:
                    count += 1
                    pair_conflicts = count * (count - 1) // 2
                    if pair_conflicts > self._k:
                        return True
        return False

    def feasibility_bound(self, context) -> List[str]:
        """Preflight: can each program's elective exams fit into their
        candidate dates without exceeding the same-day conflict cap?
        """
        selected = context.selected_set
        max_per_day = max_electives_per_day(self._k)
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
            if dates and len(program_slots) > max_per_day * len(dates):
                errors.append(
                    f"Elective conflict cap {self._k} allows at most {max_per_day} "
                    f"same-day elective exams for program {program_id}, but "
                    f"{len(program_slots)} elective exams must fit into "
                    f"{len(dates)} possible dates."
                )
                continue

            for domain, same_domain_slots in slots_by_domain(program_slots).items():
                if len(same_domain_slots) > max_per_day * len(domain):
                    errors.append(
                        f"Elective conflict cap {self._k} allows at most {max_per_day} "
                        f"same-day elective exams for program {program_id}, but "
                        f"{len(same_domain_slots)} elective exams share the same "
                        f"{len(domain)} possible dates."
                    )
        return errors
