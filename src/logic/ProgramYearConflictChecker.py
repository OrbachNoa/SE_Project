# ---------------------------------------------------------------------------
# Concrete checker 1 — program/year conflict
# ---------------------------------------------------------------------------
 
from src.logic.IConflictChecker import IConflictChecker


class ProgramYearConflictChecker(IConflictChecker):
    """
    Ensures that no two OBLIGATORY exams belonging to the same
    (program, year) pair are scheduled on the same date.
 
    Per the SRS (section 1.2):
      "No two exams from the same year in the same program on the same date,
       UNLESS both exams are ELECTIVE."
 
    Algorithm
    ---------
    For each existing assignment in the schedule:
      1. Find every (program, year) pair that both courses share.
      2. If the dates match AND at least one of the two courses is OBLIGATORY
         in that shared (program, year) → conflict.
    """
 
    def check(self, assignment, schedule) -> bool:
        new_course = assignment.course
        new_date   = assignment.date
 
        for existing in schedule.get_assignments():
            existing_course = existing.course
 
            # Same date?  (v1.0 checks date only, no hour granularity)
            if existing.date != new_date:
                continue
 
            # Find (program, year) pairs shared by both courses
            new_entries      = {(e.program_id, e.year): e for e in new_course.program_entries}
            existing_entries = {(e.program_id, e.year): e for e in existing_course.program_entries}
 
            shared_keys = set(new_entries.keys()) & set(existing_entries.keys())
 
            for key in shared_keys:
                new_req      = new_entries[key].requirement
                existing_req = existing_entries[key].requirement
 
                # Conflict only if at least one side is OBLIGATORY
                if new_req.name == "OBLIGATORY" or existing_req.name == "OBLIGATORY":
                    return True   # conflict detected → reject
 
        return False  # no conflict