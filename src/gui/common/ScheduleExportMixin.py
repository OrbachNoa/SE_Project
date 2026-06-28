"""Shared TXT/PDF/Excel export skeleton for schedule screens.

Both the output screen and the cluster-detail screen run the same export
sequence — guard that a schedule is selected, read the current schedule, guard
that it is not empty, ask for a path, save, and map any failure to a clean
message. They differ only in *how* they read/save the current schedule, build
filenames, and present errors (the output screen stays put on failure; the
cluster-detail screen routes back). Those differences are supplied by the host
presenter through the hook methods below, so the skeleton lives in one place.

A host presenter mixes this in and implements the hooks; it gets working
``on_export_pdf`` / ``on_export_txt`` / ``on_export_excel`` methods for free.
"""
from __future__ import annotations


class ScheduleExportMixin:
    """Provides on_export_{pdf,txt,excel} on top of host-supplied hooks."""

    # ── hooks the host presenter must implement ──────────────────────────────
    def _export_has_content(self) -> bool:
        """True when there is a schedule selected to export at all."""
        raise NotImplementedError

    def _export_read_schedule(self):
        """Return the current schedule view-model (may raise)."""
        raise NotImplementedError

    def _export_filename(self, ext: str) -> str:
        """Default save filename for the given extension (e.g. 'txt', 'xlsx')."""
        raise NotImplementedError

    def _export_pdf_view(self, schedule_view) -> None:
        """Hand the schedule to the view's PDF exporter."""
        raise NotImplementedError

    def _export_save_txt(self, path: str) -> None:
        raise NotImplementedError

    def _export_save_excel(self, path: str) -> None:
        raise NotImplementedError

    # presentation hooks
    def _export_nothing(self, message: str) -> None:
        """Tell the user there is nothing (or nothing non-empty) to export."""
        raise NotImplementedError

    def _export_read_error(self, error: Exception, fmt: str) -> None:
        raise NotImplementedError

    def _export_save_error(self, error: Exception, fmt: str, path: str) -> None:
        raise NotImplementedError

    def _export_saved(self, path: str) -> None:
        raise NotImplementedError

    # ── shared skeleton ──────────────────────────────────────────────────────
    def _export_load_nonempty(self, fmt: str):
        """Run the common guard + read; return a non-empty schedule view or None."""
        if not self._export_has_content():
            self._export_nothing("There is no schedule to export yet.")
            return None
        try:
            schedule_view = self._export_read_schedule()
        except Exception as error:
            self._export_read_error(error, fmt)
            return None
        if schedule_view.is_empty():
            self._export_nothing("This schedule has no exams to export.")
            return None
        return schedule_view

    def on_export_pdf(self) -> None:
        schedule_view = self._export_load_nonempty("pdf")
        if schedule_view is None:
            return
        self._export_pdf_view(schedule_view)

    def on_export_txt(self) -> None:
        schedule_view = self._export_load_nonempty("txt")
        if schedule_view is None:
            return
        path = self._view.ask_save_path(self._export_filename("txt"))
        if not path:
            return
        try:
            self._export_save_txt(path)
            self._export_saved(path)
        except Exception as error:
            self._export_save_error(error, "txt", path)

    def on_export_excel(self) -> None:
        schedule_view = self._export_load_nonempty("excel")
        if schedule_view is None:
            return
        path = self._view.ask_save_path_excel(self._export_filename("xlsx"))
        if not path:
            return
        try:
            self._export_save_excel(path)
            self._export_saved(path)
        except Exception as error:
            self._export_save_error(error, "excel", path)
