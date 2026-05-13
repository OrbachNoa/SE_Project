from src.logic.IConflictChecker import IConflictChecker
from src.models.enums import Requirement

class ProgramYearConflictChecker(IConflictChecker):
    """
    This class checks if two exams are in the same program and the same year.
    If they are, and one of them is OBLIGATORY, they cannot be on the same date.
    """
    def check(self, assignment, schedule) -> bool:
        # Get the course and the date of the new exam.
        new_course = assignment.course
        new_date = assignment.date

        # Look at every exam that is already in the schedule.
        for existing in schedule.assignments:
            
            # If the dates are different, there is no problem. Skip to the next exam.
            if existing.date != new_date:
                continue

            existing_course = existing.course

            # Create a dictionary to easily find the program and year of both courses.
            new_entries = {(e.programId, e.year): e for e in new_course.programEntries}
            existing_entries = {(e.programId, e.year): e for e in existing_course.programEntries}

            # Find if the two courses share the exact same program and the exact same year.
            shared_keys = set(new_entries.keys()) & set(existing_entries.keys())

            # If they share a program and year, check if they are obligatory.
            for key in shared_keys:
                new_req = new_entries[key].requirement
                existing_req = existing_entries[key].requirement
                
                # If at least one of them is OBLIGATORY, this is a conflict. Return True.
                if new_req.name == "OBLIGATORY" or existing_req.name == "OBLIGATORY":
                    return True

        # If we checked everything and found no problems, return False.
        return False