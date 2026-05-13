import copy
from typing import List, Tuple
from src.models.exam_schedule import ExamSchedule, ExamAssignment
from src.models.enums import Moed, Requirement

class Slot:
    """
    This class holds one task that we need to schedule.
    A task (slot) is exactly one course, in one semester, for one moed.
    """
    def __init__(self, course, semester, moed):
        self.course = course
        self.semester = semester
        self.moed = moed

class Scheduler:
    """
    This is the main brain of the program. 
    It builds the schedule step by step using an algorithm called 'Backtracking'.
    """
    def __init__(self, courses: list, periods: list, conflictCheckers: list, validators: list, selected_programs: List[str] = None):
        # Save all the inputs we need to build the schedule.
        self._courses = courses
        self._periods = periods
        self._checkers = conflictCheckers
        self._validators = validators
        
        # If no programs are selected, we use an empty list.
        if selected_programs is None:
            self._selected_programs = []
        else:
            self._selected_programs = selected_programs

    def filterCourses(self) -> list:
        """
        Find only the courses we actually need to schedule.
        """
        relevant = []
        selected_set = set(self._selected_programs)
        
        for course in self._courses:
            # If the course evaluation is not an EXAM, skip it.
            if not course.hasExam():
                continue
            
            # If no specific programs were selected, or if the course is in a selected program, we keep it.
            if not selected_set or any(e.programId in selected_set for e in course.programEntries):
                relevant.append(course)
                
        return relevant

    def _periodExists(self, semester, moed) -> bool:
        """
        This function checks if there is a valid exam period for a given semester and moed.
        """
        for p in self._periods:
            if p.semester == semester and p.moed == moed:
                return True
        return False

    def _score(self, course) -> int:
        """
        This function calculates a 'score' for a course to know how hard it is to schedule.
        Harder courses will be scheduled first to save time.
        """
        score = 0
        selected_set = set(self._selected_programs)
        
        for entry in course.programEntries:
            if not selected_set or entry.programId in selected_set:
                score = score + 1 # Add 1 point for every program the course is in.
                
                # If the course is OBLIGATORY, add 2 more points because it is harder to schedule.
                if entry.requirement == Requirement.OBLIGATORY:
                    score = score + 2
                    
        return score

    def _buildSlots(self) -> List[Slot]:
        """
        Build a list of 'Slots' (tasks) to do.
        """
        relevant_courses = self.filterCourses()
        selected_set = set(self._selected_programs)
        slots = []
        seen = set() # We use this to remember what we already added, so we don't add duplicates.
        
        for course in relevant_courses:
            semesters = set()
            for e in course.programEntries:
                if not selected_set or e.programId in selected_set:
                    semesters.add(e.semester)
            
            for sem in semesters:
                for moed in Moed:
                    # Check if the period exists before creating a slot.
                    if self._periodExists(sem, moed):
                        
                        # Create a unique key. If we already saw this exact key, we skip it.
                        key = (course.courseId, sem, moed)
                        if key not in seen:
                            seen.add(key)
                            slots.append(Slot(course, sem, moed))
                            
        # Sort the slots. The highest score (hardest course) goes first.
        slots.sort(key=lambda s: self._score(s.course), reverse=True)
        return slots

    def _getCandidates(self, slot: Slot) -> List[Tuple]:
        """
        This function returns all the allowed dates for a specific slot.
        """
        candidates = []
        for period in self._periods:
            if period.semester == slot.semester and period.moed == slot.moed:
                # Ask the period for its available dates.
                if hasattr(period, 'getAvailableDates') and callable(period.getAvailableDates):
                    dates = period.getAvailableDates()
                    if dates is not None:
                        for d in dates:
                            candidates.append((d,))
                        break
        return candidates

    def _backtrack(self, index: int, slots: List[Slot], schedule: ExamSchedule, results: list) -> None:
        """
        The Backtracking.
        It tries to put each course in a date, one by one.
        If it gets stuck, it goes back and tries a different date.
        """
        # Base Case: If the index is equal to the number of slots, we finished!
        if index == len(slots):
            # Create a full copy of the schedule so we don't lose the data.
            new_sched = ExamSchedule()
            new_sched.assignments = list(schedule.assignments)
            
            # Save the full copy in our results list.
            results.append(new_sched)
            return

        # Take the current slot we want to schedule.
        slot = slots[index]
        
        # Get all the possible dates for this slot.
        for (date,) in self._getCandidates(slot):
            
            # Create a new exam assignment object to test this date.
            assignment = ExamAssignment(course=slot.course, date=date, moed=slot.moed)
            assignment.semester = slot.semester 
            
            conflict = False
            
            # Ask every checker if this new assignment creates a problem.
            for checker in self._checkers:
                if checker.check(assignment, schedule):
                    conflict = True
                    break # Stop checking because we already found a problem.
            
            # If no checker found a problem, the date is good!
            if not conflict:
                # Add the assignment to our schedule.
                schedule.addAssignment(assignment)
                
                # Move to the next slot (index + 1) by calling this function again.
                self._backtrack(index + 1, slots, schedule, results)
                
                # When we return from the function, remove the assignment.
                # This allows us to try the next date in the loop.
                schedule.removeAssignment(assignment)

    def generateAllSchedules(self) -> list:
        """
        This is the main function that starts the whole process.
        """
        # Build the slots.
        slots = self._buildSlots()
        
        # Create an empty schedule and an empty results list.
        schedule = ExamSchedule()
        results = []
        
        # Start the backtracking process from index 0.
        self._backtrack(0, slots, schedule, results)
        
        # Return all the successful schedules we found.
        return results