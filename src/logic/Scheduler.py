from typing import List, Tuple
from src.models.exam_schedule import ExamSchedule, ExamAssignment
from src.models.enums import Moed, Requirement

class Slot:
    def __init__(self, course, semester, moed):
        self.course   = course
        self.semester = semester
        self.moed     = moed

class Scheduler:

    def __init__(self, courses: list, periods: list, conflictCheckers: list,
                 validators: list, selected_programs: List[str] = None):
        self._courses           = courses
        self._periods           = periods
        self._checkers          = conflictCheckers
        self._validators        = validators
        self._selected_programs = selected_programs or []

    # ── helpers ────────────────────────────────────────────────────────

    def filterCourses(self) -> list:
        selected_set = set(self._selected_programs)
        return [
            c for c in self._courses
            if c.hasExam() and (
                not selected_set or
                any(e.programId in selected_set for e in c.programEntries)
            )
        ]

    def _periodExists(self, semester, moed) -> bool:
        return any(p.semester == semester and p.moed == moed for p in self._periods)

    def _score(self, course) -> int:
        selected_set = set(self._selected_programs)
        score = 0
        for e in course.programEntries:
            if not selected_set or e.programId in selected_set:
                score += 1
                if e.requirement == Requirement.OBLIGATORY:
                    score += 2
        return score

    def _buildSlots(self) -> List[Slot]:
        selected_set = set(self._selected_programs)
        slots, seen  = [], set()
        for course in self.filterCourses():
            semesters = {
                e.semester for e in course.programEntries
                if not selected_set or e.programId in selected_set
            }
            for sem in semesters:
                for moed in Moed:
                    if self._periodExists(sem, moed):
                        key = (course.courseId, sem, moed)
                        if key not in seen:
                            seen.add(key)
                            slots.append(Slot(course, sem, moed))
        slots.sort(key=lambda s: self._score(s.course), reverse=True)
        return slots

    def _getCandidates(self, slot: Slot) -> List[Tuple]:
        for period in self._periods:
            if period.semester == slot.semester and period.moed == slot.moed:
                if hasattr(period, 'getAvailableDates') and callable(period.getAvailableDates):
                    dates = period.getAvailableDates()
                    if dates:
                        return [(d,) for d in dates]
        return []

    # ── backtracking ───────────────────────────────────────────────────

    def _backtrack(self, index: int, slots: List[Slot], candidates_cache: List[List[Tuple]], 
                   schedule: ExamSchedule, results: list, max_results: int) -> None:

        if len(results) >= max_results:
            return

        if index == len(slots):
            # הגענו לקצה - הפתרון חוקי. נשכפל את התוצאה.
            new_sched = ExamSchedule()
            new_sched.assignments = list(schedule.assignments)
            results.append(new_sched)
            return

        slot = slots[index]

        # שליפה מהירה מה-Cache במקום לחשב מחדש את התקופות
        for (date,) in candidates_cache[index]:
            if len(results) >= max_results:
                return

            assignment          = ExamAssignment(course=slot.course, date=date, moed=slot.moed)
            assignment.semester = slot.semester

            # הבדיקה הדינמית הקלאסית - מוודאת ששום Checker (גם אלה מהטסטים) לא מכשיל אותנו
            if not any(ck.check(assignment, schedule) for ck in self._checkers):
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, candidates_cache, schedule, results, max_results)
                schedule.removeAssignment(assignment)

    # ── entry point ────────────────────────────────────────────────────

    def generateAllSchedules(self, max_results: int = 1000000) -> list:
        slots = self._buildSlots()
        if not slots:
            return []

        # 1. אופטימיזציית מילוי מטמון: נחשב את כל התאריכים מראש לכל סלוט
        candidates_cache = []
        for slot in slots:
            candidates_cache.append(self._getCandidates(slot))

        # 2. אופטימיזציית פרה-חישוב: נחפש את ה-Checker שלנו ונכין את גרף ההתנגשויות
        # (ייקרא רק אם ה-Checker הספציפי הזה קיים ברשימה)
        py_checker = None
        for ck in self._checkers:
            if type(ck).__name__ == "ProgramYearConflictChecker":
                py_checker = ck
                break
                
        if py_checker and hasattr(py_checker, 'precompute_conflicts'):
            courses_set = {s.course for s in slots}
            py_checker.precompute_conflicts(list(courses_set))

        schedule = ExamSchedule()
        results  = []
        
        self._backtrack(0, slots, candidates_cache, schedule, results, max_results)
        
        return results