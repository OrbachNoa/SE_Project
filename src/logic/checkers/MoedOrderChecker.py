from src.logic.checkers.IConflictChecker import IConflictChecker
from src.models.Enums import Moed

class MoedOrderChecker(IConflictChecker):
    """
    Checks that each course's moeds are scheduled in the correct order.
    """
    def __init__(self):
        pass

    def check(self, assignment, schedule) -> bool:
        new_moed_rank = self._rank(assignment.moed)
        same_course = schedule.course_assignments_index().get(assignment.course.courseId)
        if not same_course:
            return False
        # Compare the new assignment with exams already placed in the schedule.
        for existing in same_course:
            # Check only exams that belong to the same course.
            existing_moed_rank = self._rank(existing.moed)

            # If the existing moed is earlier, it must also have an earlier date.
            if existing_moed_rank < new_moed_rank:
                # Reject equal or reversed dates, because the moed order is broken.
                if existing.date >= assignment.date:
                    return True

            # If the existing moed is later, it must also have a later date.
            elif existing_moed_rank > new_moed_rank:
                # Reject equal or reversed dates, because the moed order is broken.
                if existing.date <= assignment.date:
                    return True

            # Reject the same moed twice, so a course cannot be scheduled twice.
            elif existing_moed_rank == new_moed_rank:
                return True

        # Return no conflict after all existing exams pass the checks.
        return False

    def _rank(self, moed) -> int:
        if moed is Moed.ALEPH:
            return 1
        if moed is Moed.BET:
            return 2
        if moed is Moed.GIMEL:
            return 3
        return 0
