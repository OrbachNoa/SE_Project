from __future__ import annotations
from typing import Optional

from logic.observers.IScheduleObserver import IScheduleObserver
from io.writers.textFileWriter import TextFileWriter


class StreamingScheduleObserver(IScheduleObserver):
    """Writes schedules to a text file on the fly without in-memory accumulation."""

    def __init__(self, output_path: str, writer: Optional[TextFileWriter] = None) -> None:
        self._output_path = output_path
        self._writer = writer or TextFileWriter()
        self._file = None
        self._count = 0
        
        # Caches to optimize repeated date and enum formatting
        self._date_cache: dict = {}
        self._enum_cache: dict = {}
        self._error: Optional[str] = None

    def on_schedule_found(self, schedule) -> None:
        """Lazily opens the file and writes the newly found schedule directly to disk."""
        
        if self._file is None:
            self._file = open(
                self._output_path, "w", encoding="utf-8", buffering=512 * 1024
            )

        self._count += 1
        body = self._writer.formatSchedule(schedule, self._date_cache, self._enum_cache)
        self._file.write(f"=== Exam System Option {self._count} ===\n{body}\n\n")

    def on_progress(self, value: int) -> None:
        """No-op for the CLI execution path."""
        pass

    def should_cancel(self) -> bool:
        """Returns False as the CLI path always runs to completion."""
        return False

    def on_finished(self) -> None:
        """Closes the file, or writes a 'no results' marker if no schedules were found."""
        
        if self._file is not None:
            self._file.close()
            self._file = None
            return

        with open(self._output_path, "w", encoding="utf-8") as f:
            f.write("No valid exam schedules were generated.\n")

    def on_error(self, message: str) -> None:
        """Stores the error message and closes the file handle if open."""
        self._error = message
        if self._file is not None:
            self._file.close()
            self._file = None

    @property
    def count(self) -> int:
        """Returns the total number of schedules written."""
        return self._count

    @property
    def error(self) -> Optional[str]:
        """Returns the recorded error message, or None if no error occurred."""
        return self._error