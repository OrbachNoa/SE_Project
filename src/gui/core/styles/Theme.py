"""Global stylesheet and style tokens for the PyQt6 application."""

# Re-export all color constants for backward compatibility
from gui.core.styles.Palette import (
    COLOR_BG,
    COLOR_TEXT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_BORDER,
    COLOR_GOLD,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    COLOR_MUTED,
)

from gui.core.styles.GlobalStyles import GLOBAL_STYLESHEET
from gui.core.styles.HeaderStyles import HEADER_STYLESHEET
from gui.core.styles.CalendarStyles import CALENDAR_STYLESHEET
from gui.core.styles.CourseListStyles import COURSE_LIST_STYLESHEET
from gui.core.styles.ScreenStyles import SCREEN_STYLESHEET

# Aggregated application-wide stylesheet
APP_STYLESHEET = (
    GLOBAL_STYLESHEET +
    HEADER_STYLESHEET +
    CALENDAR_STYLESHEET +
    COURSE_LIST_STYLESHEET +
    SCREEN_STYLESHEET
)
