from __future__ import annotations

from collections import Counter
from typing import Dict, List, Set

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.feasibility.helpers import all_dates, min_pair_conflicts, slots_by_domain
from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex
from src.models.Enums import Requirement


class ElectiveConflictCapChecker(IConflictChecker):
    """
    Checks the elective conflict limit.

    This rule limits how many elective exam conflicts each program may have.
    A conflict is counted when two elective exams from the same program are placed
    on the same date.

    Years are ignored here on purpose, because the requirement is per program,
    not per program and year.
    """

    def __init__(self, k: int):
        self._k = k
        # Maximum elective conflict pairs allowed for one program.
        self._max_conflicts_per_program = k

        # Dict that to each program save is elective courses, use to know which course is already in assigned
        self._program_elective_sets: Dict[str, Set[str]] = {}

        # For each elective course save is program, use it to know where to assign each course
        self._course_programs: Dict[str, List[str]] = {}

        # Cache for elective date counts.
        # Key: schedule id.
        # Value: the schedule object, its version, and the counts we calculated.
        self._index_cache: Dict[int, tuple] = {}

    def _program_date_counts(self, schedule) -> Dict[str, Counter]:
        """
        Counts how many elective exams each program already has on each date.

        return to each program how much elective course is already in the current scheduler
        """
        cached = self._index_cache.get(id(schedule))

        if cached is not None:
            # The cache stores: schedule object, schedule version, and date counts.
            cached_schedule, cached_version, cached_counts = cached

            # If its the same schedule we can reuse it instead of rebuild him again
            if cached_schedule is schedule and cached_version == schedule.version:
                return cached_counts

        # If there is not cache ,build new index
        index: Dict[str, Counter] = {}
        course_assignments = schedule.course_assignments_index()

        # For each program, count how many of its elective exams are already placed on each date.
        for program_id, electives in self._program_elective_sets.items():
            counts: Counter = Counter()

            for course_id in electives:
                for assignment in course_assignments.get(course_id, ()):
                    counts[assignment.date] += 1

            # Save the date counts we calculated for this program.
            index[program_id] = counts

        # Save the counts with the schedule version they belong to.
        self._index_cache = {id(schedule): (schedule, schedule.version, index)}
        return index

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None, selected_index=None) -> None:
        """
        Builds lookup tables before the search starts.

        This keeps check() function fast, because during scheduling we only need direct
        lookups instead of scanning all courses every time.
        """

        selected_index = selected_index or SelectedProgramIndex(courses, selected_programs)

        program_elective_sets: Dict[str, Set[str]] = {}
        course_programs: Dict[str, List[str]] = {}

        for course in courses:
            for entry in selected_index.entries_for_course(course.courseId):
                # Ignore courses that are not elective course.
                if entry.requirement is not Requirement.ELECTIVE:
                    continue

                # If this program doesnt have set create one, add the course to the set
                program_elective_sets.setdefault(entry.programId, set()).add(course.courseId)

                # If the course not in the dict create for him an empty list
                owned_programs = course_programs.setdefault(course.courseId, [])
                # If the program not in the set
                # Add the program to the set of courses, means the course is elective in this program
                if entry.programId not in owned_programs:
                    owned_programs.append(entry.programId)

        self._program_elective_sets = program_elective_sets
        self._course_programs = course_programs

    def check(self, assignment, schedule) -> bool:
        """
        This function use in the search solution time
        Returns True if this assignment breaks the elective conflict limit.
        """

        programs = self._course_programs.get(assignment.course.courseId)
        # The course is not elective in any checked program.
        if not programs:
            return False

        # the amount of elective courses in each date for all the programs
        index = self._program_date_counts(schedule)

        for program_id in programs:
            #
            per_date_counts = index.get(program_id)

            if not per_date_counts:
                # No elective exams were placed for this program yet.
                continue

            # Count the conflict pairs that already exist in this program.
            existing_total = sum(n * (n - 1) // 2 for n in per_date_counts.values())

            # The new exam creates one pair with each elective already on this date.
            new_pairs = per_date_counts.get(assignment.date, 0)

            # The check if we cross the allowed max conflicts 
            if existing_total + new_pairs > self._max_conflicts_per_program:
                return True
            
        # There is no problem
        return False

    def feasibility_bound(self, context) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to catch cases where there is no chance to build a valid schedule.
        It returns a list of error messages. 
        If the list is empty, this check did not find a problem
        """

        # dict for the elective courses in the program
        by_program: Dict[str, Set] = context.selected_index.slots_by_program(
            requirement=Requirement.ELECTIVE
        )

        # Collect feasibility errors so the UI can show all problems at once.
        errors = []

        for program_id, program_slots in by_program.items():
            # take all the possible dates of slots in this program
            dates = all_dates(program_slots)

            # Check the best possible spread across all dates.
            # If even the best spread breaks the limit, no schedule can work.
            if ( dates and min_pair_conflicts(len(program_slots), len(dates))
                > self._max_conflicts_per_program
            ):
                # didnt succeed to find spread 
                errors.append(
                    f"Elective conflict cap {self._max_conflicts_per_program} cannot be met "
                    f"for program {program_id}: even spread as evenly as possible, "
                    f"{len(program_slots)} elective exams across {len(dates)} possible dates "
                    f"produce more than {self._max_conflicts_per_program} pair-conflicts."
                )
                continue

            # domain is the set of possible dates.
            # Slots with the same exact date options may be forced to conflict.
            for domain, same_domain_slots in slots_by_domain(program_slots).items():
                if (
                    min_pair_conflicts(len(same_domain_slots), len(domain))
                    > self._max_conflicts_per_program
                ):
                    errors.append(
                        f"Elective conflict cap {self._max_conflicts_per_program} cannot be met "
                        f"for program {program_id}: even spread as evenly as possible, "
                        f"{len(same_domain_slots)} elective exams sharing the same "
                        f"{len(domain)} possible dates produce more than "
                        f"{self._max_conflicts_per_program} pair-conflicts."
                    )

        return errors
