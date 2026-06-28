"""ViewModelMapper — the application/presentation boundary.

Converts domain objects (Course, ExamPeriod) and the picklable
ScheduleDTO into flat and primitive view models for the GUI.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from src.models.Course import Course
from src.models.ExamPeriod import ExamPeriod
from src.application.dto.ScheduleDTO import ScheduleDTO, AssignmentDTO
from src.application.viewmodels.ScheduleViewModel import (
    ScheduleViewModel,
    ScheduleItemViewModel,
)
from src.application.viewmodels.CalendarViewModel import (
    CalendarViewModel,
    CalendarCellViewModel,
)
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel
from src.application.viewmodels.ProgramViewModel import (
    ProgramViewModel,
    ProgramCoursesViewModel,
    CourseRowViewModel,
)
from src.application.viewmodels.ClusterViewModel import (
    ClusterCardViewModel,
    ClusterComparisonViewModel,
)
from src.logic.clustering import CriterionDisplay

# ----- helpers ---------------------------------------------------------
from data.programs import programs_data

def _program_display_name(program_id: str) -> str:
    """Derive a human readable label for a program id."""
    # Pulls the real name from the dictionary, and if the ID does not exist uses a default text name
    return programs_data.get(program_id, f"Program {program_id}")


class ViewModelMapper:
    """Stateless converter from domain/DTO inputs to GUI view models."""

    # ----- schedules -------------------------------------------------------

    def _item_from_assignment(
        self,
        a: AssignmentDTO,
        selected_programs: Optional[List[str]] = None,
    ) -> ScheduleItemViewModel:

        # Filter programs if needed. If None, just dump everything.
        if selected_programs:
            relevant_pairs = [
                (pid, req) for pid, req in a.program_requirements if pid in selected_programs
            ]
        else:
            relevant_pairs = list(a.program_requirements)

        # Plain-text program/requirement lines kept as structured data so the
        # PDF exporter / overlay don't have to parse them back out of subtitle.
        program_lines = [f"Prog {pid} ({req.capitalize()})" for pid, req in relevant_pairs]
        # Build the program req string. using <br> cuz PyQt labels support rich text HTML formatting.
        req_str = "<br>".join(program_lines)

        # Title is just the course name. Subtitle holds the ID and the colored req string.
        title = a.course_name
        subtitle = f"ID: {a.course_id}<br><span style='color: #0f766e;'>{req_str}</span>"

        # Tooltip for when someone actually hovers over this tiny box
        tooltip = (
            f"{a.course_name} ({a.course_id})\n"
            f"{a.date} · {a.semester} · Moed {a.moed}\n"
            f"Instructor: {a.instructor} · {a.evaluation}\n"
            # Strip HTML <br> tags since tooltips render plain text, not HTML.
            f"{req_str.replace('<br>', ', ')}"
        )
        return ScheduleItemViewModel(
            date=a.date,
            title=title,
            subtitle=subtitle,
            tooltip=tooltip,
            instructor=a.instructor,
            evaluation=a.evaluation,
            course_id=a.course_id,
            details=f"{a.semester} · Moed {a.moed}",
            programs=program_lines,
        )

    def to_schedule_vm(
        self,
        dto: ScheduleDTO,
        current_index: int = 0,
        total: int = 1,
        selected_programs: Optional[List[str]] = None,
    ) -> ScheduleViewModel:
        """Map a schedule DTO to a date-sorted ScheduleViewModel ("X of Y" from caller, example: "Schedule 2 of 5").

        selected_programs is the list of programme IDs the user selected before
        launching generation. It is forwarded to _item_from_assignment so each
        item's tooltip shows only the relevant programme/requirement pairs.
        Callers that omit selected_programs receive the full unfiltered tooltip
        (backward-compatible default).
        """
        if dto is None:
            raise ValueError("to_schedule_vm received None; expected a ScheduleDTO")

        # If selected_programs is None, use an empty list
        effective_programs = selected_programs if selected_programs is not None else []

        items = [self._item_from_assignment(a, effective_programs) for a in dto.assignments]
        items.sort(key=lambda item: item.date)  # ISO dates sort correctly as text
        return ScheduleViewModel(items=items, current_index=current_index, total=total, scores=dto.scores)

    def to_calendar_vm(self, dto: ScheduleDTO) -> CalendarViewModel:
        """Map a schedule DTO to year-calendar cells (one per exam day, date-sorted)."""
        if dto is None:
            raise ValueError("to_calendar_vm received None; expected a ScheduleDTO")

        # Group assignments by date; multiple exams on the same day share a cell.
        by_date: dict[str, List[ScheduleItemViewModel]] = {}
        for a in dto.assignments:
            by_date.setdefault(a.date, []).append(self._item_from_assignment(a))

        cells: List[CalendarCellViewModel] = []
        for day in sorted(by_date.keys()):
            day_items = by_date[day]
            label = "1 exam" if len(day_items) == 1 else f"{len(day_items)} exams"
            cells.append(
                CalendarCellViewModel(
                    date=day, items=day_items, is_blocked=False, tooltip=label
                )
            )
        return CalendarViewModel(cells=cells)

    # ----- periods ---------------------------------------------------------

    def to_period_edit_vms(self, periods: Iterable[ExamPeriod]) -> List[PeriodEditViewModel]:
        """Flatten exam periods into editable rows (enums -> values, dates -> ISO)."""
        result: List[PeriodEditViewModel] = []
        for p in periods or []:
            result.append(
                PeriodEditViewModel(
                    semester=p.semester.value,
                    moed=p.moed.value,
                    start_date=p.startDate.isoformat(),
                    end_date=p.endDate.isoformat(),
                    excluded_dates=sorted(d.isoformat() for d in p.excludedDates),
                )
            )
        return result

    # ----- programs --------------------------------------------------------

    def to_program_vms(self, courses: Iterable[Course]) -> List[ProgramViewModel]:
        """Group courses by program id; course_count counts exam courses only."""
        exam_counts: dict[str, int] = {}
        seen_programs: set[str] = set()

        for c in courses or []:
            # Count a course once per program even if it lists multiple entries for it.
            for pid in {entry.programId for entry in c.programEntries}:
                seen_programs.add(pid)
                exam_counts.setdefault(pid, 0)
                if c.hasExam():
                    exam_counts[pid] += 1

        return [
            ProgramViewModel(
                program_id=pid,
                display_name=_program_display_name(pid),
                course_count=exam_counts.get(pid, 0),
            )
            for pid in sorted(seen_programs)
        ]

    def to_program_courses_vm(self, courses: Iterable[Course]) -> List[ProgramCoursesViewModel]:
        """Expand courses into one ProgramCoursesViewModel per program.

        year/semester/requirement come from that program's entry; all courses are
        included, with is_exam_relevant flagging the scheduled ones.
        """
        rows_by_program: dict[str, List[CourseRowViewModel]] = {}

        for c in courses or []:
            for entry in c.programEntries:
                row = CourseRowViewModel(
                    course_id=c.courseId,
                    course_name=c.name,
                    year=entry.year,
                    semester=entry.semester.value,
                    requirement=entry.requirement.value,
                    evaluation=c.evaluation.value,
                    instructor=c.instructor,
                    is_exam_relevant=c.hasExam(),
                )
                rows_by_program.setdefault(entry.programId, []).append(row)

        result: List[ProgramCoursesViewModel] = []
        for pid in sorted(rows_by_program.keys()):
            # Sort courses within each program by course_id for consistent display order.
            rows = sorted(rows_by_program[pid], key=lambda r: r.course_id)
            result.append(
                ProgramCoursesViewModel(
                    program_id=pid,
                    program_name=_program_display_name(pid),
                    courses=rows,
                )
            )
        return result

    # ----- clusters --------------------------------------------------------

    def to_cluster_cards(self, result) -> List[ClusterCardViewModel]:
        """Map a ClusterResult into overview cards (one per family)."""
        criteria = result.criteria
        
        # Calculate stats (mean, std) for each criterion across all clusters
        stats = {}
        for crit in criteria:
            vals = [c.summary.get(crit, 0.0) for c in result.clusters]
            mean = sum(vals) / len(vals) if vals else 0.0
            variance = sum((v - mean) ** 2 for v in vals) / len(vals) if vals else 0.0
            std = variance ** 0.5
            stats[crit] = (mean, std)

        cards: List[ClusterCardViewModel] = []
        for cluster in result.clusters:
            # Find defining criterion based on largest absolute Z-score deviation
            defining_criterion = ""
            max_abs_z = -1.0
            for crit in criteria:
                mean, std = stats.get(crit, (0.0, 0.0))
                val = cluster.summary.get(crit, 0.0)
                if std > 1e-9:
                    z = (val - mean) / std
                    if abs(z) > max_abs_z:
                        max_abs_z = abs(z)
                        defining_criterion = crit

            # Format ranges for display
            min_max_vm = {}
            for name in criteria:
                mi, ma = getattr(cluster, "min_max", {}).get(name, (0.0, 0.0))
                min_max_vm[name] = (
                    CriterionDisplay.display_value(name, mi),
                    CriterionDisplay.display_value(name, ma)
                )

            summary = [
                (name,
                 CriterionDisplay.label(name),
                 CriterionDisplay.display_value(name, cluster.summary.get(name, 0.0)))
                for name in criteria
            ]
            
            cards.append(
                ClusterCardViewModel(
                    cluster_id=cluster.cluster_id,
                    title=f"Family {cluster.cluster_id + 1}",
                    size=cluster.size,
                    estimated_population_size=cluster.estimated_population_size,
                    sampled=result.sampled,
                    description=cluster.description or "",
                    criteria=tuple(result.criteria),
                    summary=cluster.summary,
                    defining_criterion=defining_criterion,
                    min_max=min_max_vm,
                )
            )
        return cards

    def to_cluster_comparison(
        self,
        result,
        cluster_a,
        cluster_b,
        rep_dto_a: ScheduleDTO,
        rep_dto_b: ScheduleDTO,
        selected_programs: Optional[List[str]] = None,
    ) -> ClusterComparisonViewModel:
        """Build a side-by-side comparison of two families' representatives.

        The two representative schedules are rendered as schedule view models; the
        feature table lists each criterion's value for both archetypes and flags
        the rows that differ, so the GUI can highlight the real distinctions.
        """
        left_vm = self.to_schedule_vm(rep_dto_a, selected_programs=selected_programs)
        right_vm = self.to_schedule_vm(rep_dto_b, selected_programs=selected_programs)

        feats_a = cluster_a.representative_features or {}
        feats_b = cluster_b.representative_features or {}
        rows = []
        left_features_display = {}
        right_features_display = {}
        better_by_criterion = {}
        for name in result.criteria:
            raw_a = feats_a.get(name, 0.0)
            raw_b = feats_b.get(name, 0.0)
            la = CriterionDisplay.display_value(name, raw_a)
            lb = CriterionDisplay.display_value(name, raw_b)
            rows.append((name, CriterionDisplay.label(name), la, lb, la != lb))
            left_features_display[name] = la
            right_features_display[name] = lb

            # Decide the better side from the raw numeric scores (not the display
            # strings), so the comparison view doesn't have to parse "%" text.
            if raw_a == raw_b:
                better_by_criterion[name] = ""
            else:
                lower_better = CriterionDisplay.is_lower_better(name)
                a_better = (raw_a < raw_b) if lower_better else (raw_a > raw_b)
                better_by_criterion[name] = "left" if a_better else "right"

        # Build composite ratings for both families
        left_labels = self._compute_composite_labels(cluster_a, result.clusters)
        right_labels = self._compute_composite_labels(cluster_b, result.clusters)

        return ClusterComparisonViewModel(
            left_title=f"Family {cluster_a.cluster_id + 1}",
            right_title=f"Family {cluster_b.cluster_id + 1}",
            left_schedule=left_vm,
            right_schedule=right_vm,
            feature_rows=rows,
            left_student_comfort=left_labels["student_comfort"],
            left_admin_load=left_labels["admin_load"],
            left_faculty_impact=left_labels["faculty_impact"],
            left_schedule_spread=left_labels["schedule_spread"],
            right_student_comfort=right_labels["student_comfort"],
            right_admin_load=right_labels["admin_load"],
            right_faculty_impact=right_labels["faculty_impact"],
            right_schedule_spread=right_labels["schedule_spread"],
            left_features=left_features_display,
            right_features=right_features_display,
            better_by_criterion=better_by_criterion,
        )

    def _compute_composite_labels(self, cluster, all_clusters) -> dict:
        """Derive human-readable composite quality labels for a cluster.

        Compares this cluster's scores against all others to determine if it
        ranks High / Medium / Low (or Wide / Balanced / Compressed for spread).
        """
        from src.logic.comparators.ScheduleScorer import (
            MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, ELECTIVE_CONFLICTS,
            MANDATORY_SPAN, MAX_EXAMS_PER_DAY,
        )
        from src.logic.clustering.CriterionDisplay import display_value_to_percentage

        def _percentile(crit, cluster, all_clusters):
            """Rank this cluster on crit as a 0-100 percentile vs all clusters."""
            score = display_value_to_percentage(
                crit,
                CriterionDisplay.display_value(crit, cluster.summary.get(crit, 0.0))
            )
            return score

        def _hml(score):
            if score >= 65:
                return "High"
            elif score >= 35:
                return "Medium"
            return "Low"

        def _spread(score):
            if score >= 65:
                return "Wide"
            elif score >= 35:
                return "Balanced"
            return "Compressed"

        # Student Comfort: driven by min mandatory gap + avg gap
        gap_score = _percentile(MIN_MANDATORY_GAP, cluster, all_clusters)
        avg_score = _percentile(AVG_ALL_COURSES_GAP, cluster, all_clusters)
        comfort_score = (gap_score + avg_score) // 2

        # Admin Load: driven by elective conflicts + max exams per day (lower = easier admin)
        elec_score = _percentile(ELECTIVE_CONFLICTS, cluster, all_clusters)
        epd_score = _percentile(MAX_EXAMS_PER_DAY, cluster, all_clusters)
        # High admin load means fewer conflicts/crowding (score inversely)
        admin_score = (elec_score + epd_score) // 2

        # Faculty Impact: driven by max exams per day (heavier = more faculty load)
        faculty_score = _percentile(MAX_EXAMS_PER_DAY, cluster, all_clusters)

        # Schedule Spread: driven by mandatory span
        spread_score = _percentile(MANDATORY_SPAN, cluster, all_clusters)

        return {
            "student_comfort": _hml(comfort_score),
            "admin_load": _hml(admin_score),
            "faculty_impact": _hml(faculty_score),
            "schedule_spread": _spread(spread_score),
        }
