from src.logic.IConflictChecker import IConflictChecker
from src.models.enums import Requirement

class ProgramYearConflictChecker(IConflictChecker):

    def __init__(self):
        self._conflict_graph = None

    def precompute_conflicts(self, courses: list) -> None:
        self._conflict_graph = {c.courseId: set() for c in courses}

        for i, c1 in enumerate(courses):
            entries1 = {(e.programId, e.year): e for e in c1.programEntries}
            for c2 in courses[i + 1:]:
                entries2 = {(e.programId, e.year): e for e in c2.programEntries}
                
                for key in entries1.keys() & entries2.keys():
                    if (entries1[key].requirement == Requirement.OBLIGATORY or
                            entries2[key].requirement == Requirement.OBLIGATORY):
                        self._conflict_graph[c1.courseId].add(c2.courseId)
                        self._conflict_graph[c2.courseId].add(c1.courseId)
                        break

    def check(self, assignment, schedule) -> bool:
        new_date = assignment.date
        new_course = assignment.course

        if self._conflict_graph is not None:
            new_id = new_course.courseId
            conflicts = self._conflict_graph.get(new_id, set())
            
            for existing in schedule.assignments:
                if existing.date == new_date and existing.course.courseId in conflicts:
                    return True
            return False

        for existing in schedule.assignments:
            if existing.date != new_date:
                continue

            new_entries      = {(e.programId, e.year): e for e in new_course.programEntries}
            existing_entries = {(e.programId, e.year): e for e in existing.course.programEntries}

            for key in new_entries.keys() & existing_entries.keys():
                if (new_entries[key].requirement      == Requirement.OBLIGATORY or
                        existing_entries[key].requirement == Requirement.OBLIGATORY):
                    return True

        return False