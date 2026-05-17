from src.logic.IConflictChecker import IConflictChecker
from src.models.enums import Moed

class MoedOrderChecker(IConflictChecker):
    """
    Checks that each course's moeds are scheduled in the correct order.
    """
    def __init__(self):
        # Give each moed a rank, so we can compare their order.
        self._moed_rank = {
            Moed.ALEPH: 1,
            Moed.BET: 2,
            Moed.GIMEL: 3
        }

    def check(self, assignment, schedule) -> bool:
        new_course_id = assignment.course.courseId
        new_moed_rank = self._moed_rank.get(assignment.moed, 0)

        # Compare the new assignment with exams already placed in the schedule.
        for existing in schedule.assignments:
            # Check only exams that belong to the same course.
            if existing.course.courseId == new_course_id:
                existing_moed_rank = self._moed_rank.get(existing.moed, 0)

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
