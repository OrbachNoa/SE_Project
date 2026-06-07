""" CourseListWidget
PyQt5 widget that displays expandable/collapsible program rows.
Each program row can be expanded to reveal its courses, grouped by academic year and semester.
"""

from typing import Dict, List

# Updated imports for PyQt6 core and widget components
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal helper: a single course row inside an expanded program
class _CourseRow(QWidget):
    """One row displaying a single course's details."""

    # Green-tinted left border for exam-relevant courses
    EXAM_STYLE = "background-color: #F0FAF5; border-left: 3px solid #16A34A; border-radius: 0 4px 4px 0;"
    # Neutral left border for all other courses
    DEFAULT_STYLE = "background-color: #F8FAFC; border-left: 3px solid #E2E8F0; border-radius: 0 4px 4px 0;"

    def __init__(self, course_vm, parent=None):
        """
        course_vm: CourseRowViewModel
            .course_id: str
            .course_name: str
            .year: int
            .semester: str
            .requirement: str    (e.g. "Obligatory" / "Elective")
            .evaluation: str     (e.g. "Exam" / "Project" / "Attendance")
            .is_exam_relevant: bool
        """
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        # Compact fixed height keeps the course list dense and readable
        self.setFixedHeight(36)

        # Course ID — narrow fixed column, subdued slate colour
        id_lbl = QLabel(course_vm.course_id)
        id_lbl.setFixedWidth(44)
        id_lbl.setFont(QFont("Segoe UI", 10))
        id_lbl.setStyleSheet("color: #64748B;")
        layout.addWidget(id_lbl)

        # Course name — stretches to fill remaining horizontal space
        name_lbl = QLabel(course_vm.course_name)
        name_lbl.setFont(QFont("Segoe UI", 12))
        name_lbl.setStyleSheet("color: #1E293B;")
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_lbl, stretch=1)

        # Requirement badge — compact pill: green for Obligatory, amber for Elective.
        # Evaluation badge and exam icon removed to reduce visual noise.
        req_lbl = QLabel(course_vm.requirement)
        req_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if "Obligatory" in course_vm.requirement:
            req_color, req_bg = "#16A34A", "#E8F5E9"
        else:
            req_color, req_bg = "#92400E", "#FEF3C7"
        req_lbl.setStyleSheet(
            f"color: {req_color}; background: {req_bg}; "
            "border-radius: 4px; padding: 1px 6px; font-size: 11px;"
        )
        layout.addWidget(req_lbl)

        border = self.EXAM_STYLE if course_vm.is_exam_relevant else self.DEFAULT_STYLE
        self.setStyleSheet(f"QWidget {{ {border} }}")

# Internal helper: one expandable program block
class _ProgramBlock(QWidget):
    """
    A collapsible block for one program.
    Header shows program name + course count; body shows course rows.
    """

    # Dark green header matching the brand palette; Segoe UI for readability
    HEADER_STYLE = (
        "QPushButton {"
        "  background-color: #3396ad; color: #FDFBF7; border-radius: 8px;"
        "  text-align: left; padding: 8px 14px;"
        "  font-family: 'Segoe UI'; font-size: 12px; font-weight: 600;"
        "}"
        "QPushButton:hover { background-color: #297B8F; }"
    )

    def __init__(self, program_vm, parent=None):
        """
        program_vm: ProgramCoursesViewModel
            .program_id: str
            .program_name: str
            .courses: List[CourseRowViewModel]
        """
        super().__init__(parent)

        self._expanded = False
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header button — course count removed to keep the label concise
        header_text = f"▶  {program_vm.program_id} — {program_vm.program_name}"
        self._header_btn = QPushButton(header_text)
        self._header_btn.setStyleSheet(self.HEADER_STYLE)
        self._header_btn.setFixedHeight(40)
        self._header_btn.clicked.connect(self._toggle)
        root.addWidget(self._header_btn)

        # Body
        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(4, 4, 4, 4)
        body_layout.setSpacing(2)

        # Group courses by year + semester
        groups: Dict[str, List] = {}
        for c in program_vm.courses:
            key = f"Year {c.year} — Semester {c.semester}"
            groups.setdefault(key, []).append(c)

        for group_key in sorted(groups.keys()):
            # Year/semester sub-header — light blue band separating groups
            group_lbl = QLabel(group_key)
            group_lbl.setFont(QFont("Segoe UI", 11))
            group_lbl.setStyleSheet(
                "color: #3E352F; background: #FAF5EC; padding: 4px 12px; "
                "border-radius: 6px; font-weight: 600; margin: 4px 0px;"
            )
            body_layout.addWidget(group_lbl)

            for course_vm in groups[group_key]:
                row = _CourseRow(course_vm)
                body_layout.addWidget(row)

        self._body.setVisible(False)
        root.addWidget(self._body)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)

        current = self._header_btn.text()
        if self._expanded:
            new_text = current.replace("▶", "▼", 1)
        else:
            new_text = current.replace("▼", "▶", 1)
        self._header_btn.setText(new_text)

    def expand(self) -> None:
        if not self._expanded:
            self._toggle()

    def collapse(self) -> None:
        if self._expanded:
            self._toggle()


# Main widget

class CourseListWidget(QWidget):
    """ 
    Displays a scrollable list of expandable program blocks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks: Dict[str, _ProgramBlock] = {}
        # Track live rendered blocks to prevent layout memory leaks on re-renders
        self._active_widgets: List[QWidget] = []
        self._build_ui()
    
    # UI construction
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Title is intentionally absent here — the parent card in input_screen.py
        # provides the "📋  Courses" heading so it is not duplicated.

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 8px; }")

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(6, 6, 6, 6)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        root.addWidget(scroll)

    # Public API
    def render(self, programs_vm) -> None:
        """
        Populate the widget from a list of ProgramCoursesViewModel objects.

        programs_vm: List[ProgramCoursesViewModel]
            Each item must have:
              .program_id: str
              .program_name: str
              .courses: List[CourseRowViewModel]
        """
        # Clear existing blocks
        self._blocks.clear()
        for widget in self._active_widgets:
            self._container_layout.removeWidget(widget)
            widget.deleteLater()
        self._active_widgets.clear()

        if not programs_vm:
            # Set placeholder text in English to match course standards
            empty_lbl = QLabel("No study programs loaded into registry context.")
            # Use fully qualified alignment flag for PyQt6 compliance
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            self._container_layout.insertWidget(0, empty_lbl)
            return

        for vm in programs_vm:
            block = _ProgramBlock(vm)
            self._blocks[vm.program_id] = block
            self._active_widgets.append(block)
            self._container_layout.insertWidget(
                self._container_layout.count() - 1, block
            )

    def expand(self, program_id: str) -> None:
        """Expand the block for the given program ID."""
        block = self._blocks.get(program_id)
        if block:
            block.expand()

    def collapse(self, program_id: str) -> None:
        """Collapse the block for the given program ID."""
        block = self._blocks.get(program_id)
        if block:
            block.collapse()
