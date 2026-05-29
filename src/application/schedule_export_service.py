"""Service for exporting a generated schedule to a file."""
from __future__ import annotations

import os

from src.models.exam_schedule import ExamSchedule
from src.writers.outputWriter import OutputWriter


class ScheduleExportService:
    """Writes a selected schedule to disk via the injected OutputWriter."""

    def __init__(self, writer: OutputWriter) -> None:
        self._writer = writer

    def export(self, schedule: ExamSchedule, path: str) -> None:
        """Write a single schedule to path. Raises on empty schedule or bad path."""
        if schedule is None or not schedule.assignments:
            raise ValueError("cannot export an empty schedule")

        directory = os.path.dirname(path) or "."
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"output directory does not exist: {directory}")

        # OutputWriter.write takes a list; a single schedule is wrapped in one.
        self._writer.write([schedule], path)