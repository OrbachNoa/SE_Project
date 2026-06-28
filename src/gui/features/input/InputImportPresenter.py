"""Owns courses/periods file import state and the import flow itself.

Split out of InputScreenPresenter (the "import" concern): asks the view for a
file path, hands it to the controller, and reports success/failure back to
the view. Knows nothing about generation, constraints, or Generate-button
gating — the caller is notified via on_loaded whenever loaded state changes,
so it can re-gate the button itself.
"""
from __future__ import annotations

from typing import Callable

from src.application.ImportBoundary import ImportMode


class InputImportPresenter:
    """Loads courses/periods files and tracks whether each has been loaded."""

    def __init__(self, view, controller, on_loaded: Callable[[], None]) -> None:
        self._view = view
        self._controller = controller
        self._on_loaded = on_loaded

        self.courses_loaded = False
        self.periods_loaded = False

    # Handles the actual file loading process for courses
    def on_load_courses(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select courses file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "courses", mode)
        if not self._handle_import_result(result, "courses"):
            return

        self.courses_loaded = True
        self._view.mark_courses_loaded(result.loaded_count)

        # After loading, narrow the selectable programs to those in the file,
        # then render the course list, before refreshing the generate button -
        # the button's validation depends on the now-updated program selection.
        courses = self._controller.get_loaded_courses()
        mapper = self._controller.get_mapper()
        if courses and mapper is not None:
            self._view.set_available_programs(mapper.to_program_vms(courses))
            self._view.render_courses(mapper.to_program_courses_vm(courses))

        self._on_loaded()

    # Handles the actual file loading process for periods
    def on_load_periods(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select periods file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "periods", mode)
        if not self._handle_import_result(result, "periods"):
            return

        self.periods_loaded = True
        self._view.mark_periods_loaded(result.loaded_count)
        self._on_loaded()

        # After loading, show the period editor if data is valid
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if not periods or mapper is None:
            return

        period_vms = mapper.to_period_edit_vms(periods)
        if period_vms:
            self._view.show_period_editor(period_vms)

    # Handles and displays errors that happen during file import
    def _handle_import_result(self, result, data_label: str) -> bool:
        if result.success:
            return True

        detail = "\n".join(result.errors) if result.errors else "Unknown error."
        self._view.show_import_error(data_label, detail)
        return False
