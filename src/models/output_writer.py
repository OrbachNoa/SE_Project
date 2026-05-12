from abc import ABC, abstractmethod
from typing import List
from src.models.exam_schedule import ExamSchedule, ExamAssignment

class OutputWriter(ABC):
    """
    Abstract base class for all output formats.
    """

    @abstractmethod
    def write(self, schedules: List[ExamSchedule], path: str) -> None:
        """
        Write all generated schedules to a file.
        """
        pass

    @abstractmethod
    def _formatSchedule(self, s: ExamSchedule) -> str:
        """
        Format a single schedule.
        """
        pass

    @abstractmethod
    def _formatAssignment(self, a: ExamAssignment) -> str:
        """
        Format a single assignment.
        """
        pass