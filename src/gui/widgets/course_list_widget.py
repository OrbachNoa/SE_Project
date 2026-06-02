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

    EXAM_STYLE = "background-color: #fef9c3; border-left: 3px solid #ca8a04;"
    DEFAULT_STYLE = "background-color: #f8fafc; border-left: 3px solid #e2e8f0;"

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
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        # Course ID
        id_lbl = QLabel(course_vm.course_id)
        id_lbl.setFixedWidth(72)
        id_lbl.setFont(QFont("Courier New", 10, QFont.Bold))
        id_lbl.setStyleSheet("color: #475569;")
        layout.addWidget(id_lbl)

        # Course name
        name_lbl = QLabel(course_vm.course_name)
        name_lbl.setFont(QFont("Arial", 10))
        name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(name_lbl)

        # Requirement badge
        req_lbl = QLabel(course_vm.requirement)
        req_lbl.setFixedWidth(50)
        req_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        req_lbl.setFont(QFont("Arial", 9))
        req_color = "#1d4ed8" if "Obligatory" in course_vm.requirement else "#6b7280"
        req_lbl.setStyleSheet(
            f"color: {req_color}; background: #eff6ff; "
            "border-radius: 4px; padding: 1px 3px;"
        )
        layout.addWidget(req_lbl)

        # Evaluation badge
        eval_lbl = QLabel(course_vm.evaluation)
        eval_lbl.setFixedWidth(80)
        eval_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eval_lbl.setFont(QFont("Arial", 9))
        if course_vm.is_exam_relevant:
            eval_lbl.setStyleSheet(
                "color: #92400e; background: #fef3c7; border-radius: 4px; "
                "padding: 1px 3px; font-weight: bold;"
            )
        else:
            eval_lbl.setStyleSheet(
                "color: #6b7280; background: #f3f4f6; border-radius: 4px; padding: 1px 3px;"
            )
        layout.addWidget(eval_lbl)

        # Exam icon
        if course_vm.is_exam_relevant:
            exam_icon = QLabel("📋")
            exam_icon.setToolTip("This course is relevant for exams")
            layout.addWidget(exam_icon)

        border = self.EXAM_STYLE if course_vm.is_exam_relevant else self.DEFAULT_STYLE
        self.setStyleSheet(f"QWidget {{ {border} border-radius: 4px; }}")

# Internal helper: one expandable program block
class _ProgramBlock(QWidget):
    """
    A collapsible block for one program.
    Header shows program name + course count; body shows course rows.
    """

    HEADER_STYLE = (
        "QPushButton {"
        "  background-color: #1e40af; color: white; border-radius: 6px;"
        "  text-align: left; padding: 8px 12px; font-size: 12px; font-weight: bold;"
        "}"
        "QPushButton:hover { background-color: #1d4ed8; }"
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

        # Header button
        course_count = len(program_vm.courses)
        header_text = (
            f"▶  {program_vm.program_id}  —  {program_vm.program_name}"
            f"  ({course_count} Courses)"
        )
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
            # Group header
            group_lbl = QLabel(group_key)
            group_lbl.setFont(QFont("Arial", 10, QFont.Bold))
            group_lbl.setStyleSheet(
                "color: #1e3a5f; background: #dbeafe; padding: 3px 8px; border-radius: 3px;"
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
        self._build_ui()
    
    # UI construction
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Title
        title = QLabel("Courses by program")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(title)

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
