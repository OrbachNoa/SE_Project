from abc import ABC, abstractmethod
from typing import List
from src.models.domain import ExamSchedule

# Defines the export contract to decouple the Scheduler from specific storage formats.
class OutputWriter(ABC):
    
    @abstractmethod
    def write(self, schedules: List[ExamSchedule], path: str) -> None:
        """
        Abstract method to write the generated exam schedules to a specific path.
        Must be implemented by concrete subclasses like TextFileWriter.
        """
        pass