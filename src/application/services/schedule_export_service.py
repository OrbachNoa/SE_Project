from __future__ import annotations

from pathlib import Path

from io.writers.outputWriter import OutputWriter
from application.dto.schedule_dto import ScheduleDTO
from application.dto.ScheduleDTOAdapter import ScheduleDTOAdapter


class ScheduleExportService:
    """Persists a user-chosen ScheduleDTO via the existing OutputWriter."""

    def __init__(self, writer: OutputWriter) -> None:
        # Injected writer decouples the service from concrete file formats (DIP).
        self._writer = writer

    def save(self, schedule_dto: ScheduleDTO, path: str) -> None:
        """Adapt the DTO and delegate to the writer."""

        # Ensure the output directory exists so a user-chosen path from a file dialog does not cause a mid-write failure.
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        adapted = ScheduleDTOAdapter(schedule_dto)
        self._writer.write([adapted], path)

    def format(self, schedule_dto: ScheduleDTO) -> str:
        """Return a readable preview string for the GUI.

        The same writer that performs the disk write exposes formatSchedule()
        for in-memory rendering; we reuse it through the adapter so the on-disk
        file and the preview are identical.
        """
        adapted = ScheduleDTOAdapter(schedule_dto)
        # formatSchedule is part of the OutputWriter contract, so call it directly.
        return self._writer.formatSchedule(adapted)