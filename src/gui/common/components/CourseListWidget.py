""" 
CourseListWidget
PyQt6 widget that displays expandable/collapsible program rows.
Each program row can be expanded to reveal its courses, grouped by academic year and semester.
"""

from typing import Dict, List
from PyQt6.QtCore import Qt
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
        id_lbl.setObjectName("course-id-lbl")
        layout.addWidget(id_lbl)

        # Course name — stretches to fill remaining horizontal space
        name_lbl = QLabel(course_vm.course_name)
        name_lbl.setObjectName("course-name-lbl")
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_lbl, stretch=1)

        # Requirement badge — compact pill: green for Obligatory, amber for Elective.
        req_lbl = QLabel(course_vm.requirement)
        req_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if "Obligatory" in course_vm.requirement:
            req_lbl.setObjectName("badge-ok")
        else:
            req_lbl.setObjectName("badge-warning")
        layout.addWidget(req_lbl)

        if course_vm.is_exam_relevant:
            self.setObjectName("course-row-exam")
        else:
            self.setObjectName("course-row-default")

# Internal helper: one expandable program block
class _ProgramBlock(QWidget):

    def __init__(self, program_vm, parent=None):
        super().__init__(parent)

        self._expanded = False
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header button — course count removed to keep the label concise
        header_text = f"►  {program_vm.program_id} — {program_vm.program_name}"
        self._header_btn = QPushButton(header_text)
        self._header_btn.setObjectName("course-list-header-btn")
        self._header_btn.setFixedHeight(40)
        self._header_btn.setCheckable(True)
        self._header_btn.toggled.connect(self._set_expanded)
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

        # Year/semester sub-header
        for group_key in sorted(groups.keys()):
            group_lbl = QLabel(group_key)
            group_lbl.setObjectName("course-group-lbl")
            body_layout.addWidget(group_lbl)

            # Courses
            for course_vm in groups[group_key]:
                row = _CourseRow(course_vm)
                body_layout.addWidget(row)

        self._body.setVisible(False)
        root.addWidget(self._body)

    def _set_expanded(self, expanded: bool) -> None:
        """Apply the expanded state emitted by the header button."""
        self._expanded = expanded
        self._body.setVisible(self._expanded)

        current = self._header_btn.text()
        if self._expanded:
            new_text = current.replace("►", "▼", 1)
        else:
            new_text = current.replace("▼", "►", 1)
        self._header_btn.setText(new_text)

    def _toggle(self) -> None:
        """Toggle the program block open or closed."""
        self._header_btn.setChecked(not self._expanded)

    def expand(self) -> None:
        """Expand the program block."""
        if not self._expanded:
            self._header_btn.setChecked(True)

    def collapse(self) -> None:
        """Collapse the program block."""
        if self._expanded:
            self._header_btn.setChecked(False)


# Main widget - Displays a scrollable list of expandable program blocks.
class CourseListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks: Dict[str, _ProgramBlock] = {}
        # Track live rendered blocks to prevent layout memory leaks on re-renders
        self._active_widgets: List[QWidget] = []
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the UI of the CourseListWidget."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("course-scroll-area")

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(6, 6, 6, 6)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        root.addWidget(scroll)

    def render(self, programs_vm) -> None:
        """
        Populate the widget from a list of ProgramCoursesViewModel objects.
        """
        # Clear existing blocks
        self._blocks.clear()
        for widget in self._active_widgets:
            self._container_layout.removeWidget(widget)
            widget.deleteLater()
        self._active_widgets.clear()

        # Display empty state if no programs are loaded
        if not programs_vm:
            empty_lbl = QLabel("No study programs loaded into context.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setObjectName("course-empty-lbl")
            self._container_layout.insertWidget(0, empty_lbl)
            return
        
        # Add program blocks
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
