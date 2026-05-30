from __future__ import annotations

from src.infrastructure.io_persistence_validation.outputWriter import OutputWriter
from src.application.dto_viewmodel.schedule_dto import ScheduleDTO
from src.application.dto_viewmodel.schedule_dto_adapter import ScheduleDTOAdapter


class ScheduleExportService:
    """Persists a user-chosen ScheduleDTO via the existing OutputWriter."""

    def __init__(self, writer: OutputWriter) -> None:
        # Injected writer decouples the service from concrete file formats (DIP).
        self._writer = writer



    def save(self, schedule_dto: ScheduleDTO, path: str) -> None:
        """Adapt the DTO and delegate to the writer."""
        adapted = ScheduleDTOAdapter(schedule_dto)
        self._writer.write([adapted], path)

    def format(self, schedule_dto: ScheduleDTO) -> str:
        """Return a readable preview string for the GUI.

        The same TextFileWriter that performs the disk write exposes
        formatSchedule() for in-memory rendering; we reuse it through
        the adapter so the on-disk file and the preview are identical.
        """
        adapted = ScheduleDTOAdapter(schedule_dto)

        # All current OutputWriter implementations expose formatSchedule.
        # Duck-typed access keeps the field typed as the abstract
        # OutputWriter while still reusing the writer's logic.
        formatter = getattr(self._writer, "formatSchedule", None)
        if formatter is None:
            raise NotImplementedError(
                f"{type(self._writer).__name__} does not support inline formatting"
            )
        return formatter(adapted)