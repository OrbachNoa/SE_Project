"""Action bar widget containing file loader triggers, import mode toggle, and scheduler run controls."""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup, QWidget
from PyQt6.QtCore import Qt        
from PyQt6.QtGui import QIcon
from gui.common.helpers import create_scaled_pixmap, create_vertical_divider

# This class builds the main control panel (toolbar) for the screen.
# It holds the buttons to upload files, choose settings, and start the schedule generation.
class ActionBarWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        # Lock the height of the bar so it doesn't stretch, and give it a name for CSS styling later.
        self.setFixedHeight(56)
        self.setObjectName("action-bar")
        
        # Use a horizontal layout so all the buttons sit side-by-side from left to right.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # Create the button that lets the user select their "Courses" file.
        self.courses_load_btn = QPushButton("  Load Courses")
        self.courses_load_btn.setObjectName("btn-secondary")
        self.courses_load_btn.setFixedHeight(36)
        
        # Try to load a nice icon image for the button. If the image file is missing, use a text emoji instead.
        try:
            courses_pix = create_scaled_pixmap(self, "data/assets/courseIcon.png", 18)
            self.courses_load_btn.setIcon(QIcon(courses_pix))
        except Exception:
            self.courses_load_btn.setText("📂  Load Courses")
        layout.addWidget(self.courses_load_btn)

        # Create the button that lets the user select their "Periods" (dates) file.
        self.periods_load_btn = QPushButton("  Load Periods")
        self.periods_load_btn.setObjectName("btn-secondary")
        self.periods_load_btn.setFixedHeight(36)
        
        # Same as above: try to load an image, fallback to an emoji if it fails.
        try:
            periods_pix = create_scaled_pixmap(self, "data/assets/periodIcon.png", 18)
            self.periods_load_btn.setIcon(QIcon(periods_pix))
        except Exception:
            self.periods_load_btn.setText("📅  Load Periods")
        layout.addWidget(self.periods_load_btn)

        # Add a visual dividing line to separate the upload buttons from the settings area.
        v_sep = create_vertical_divider(self)
        layout.addWidget(v_sep)
        
        # Create radio buttons to let the user decide if uploading a new file should replace the old one or just update it.
        mode_label = QLabel("Mode:")
        mode_label.setObjectName("mode-label")
        self.mode_replace = QRadioButton("Replace")
        self.mode_replace.setChecked(True)
        self.mode_update = QRadioButton("Update")
        
        # Group the radio buttons together so the user can only select one option at a time.
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_replace)
        self.mode_group.addButton(self.mode_update)
        
        # Add the mode settings to the layout, and add a "stretch" (an invisible spring) to push the next buttons to the far right.
        layout.addWidget(mode_label)
        layout.addWidget(self.mode_replace)
        layout.addWidget(self.mode_update)
        layout.addStretch()

        # Create the main "Generate Schedule" button. It starts disabled (grayed out) until the user actually loads some files.
        self.generate_btn = QPushButton("▶  Generate Schedule")
        self.generate_btn.setObjectName("btn-primary")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setFixedHeight(40)
        layout.addWidget(self.generate_btn)
        
        # Create a "Cancel" button to stop the generation if it takes too long. It is hidden until the process actually starts.
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("btn-danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(40)
        layout.addWidget(self.cancel_btn)
        
        # Create a "View Results" button to jump to the final schedule. It is hidden until the schedule is successfully created.
        self.view_results_btn = QPushButton("   View Results")
        self.view_results_btn.setObjectName("btn-secondary")
        self.view_results_btn.setVisible(False)
        self.view_results_btn.setFixedHeight(40)
        
        # Try to load a checkmark icon for the results button, fallback to an eye emoji if it fails.
        try:
            view_pix = create_scaled_pixmap(self, "data/assets/verify.png", 18)
            self.view_results_btn.setIcon(QIcon(view_pix))
        except Exception:
            self.view_results_btn.setText("👁  View Results")
        layout.addWidget(self.view_results_btn)