"""Presentation logic for the input screen."""
from __future__ import annotations

from typing import List

from src.application.ImportBoundary import ImportMode
from gui.features.input.ConstraintsPresenter import ConstraintsPresenter
from gui.features.input.GenerationPresenter import GenerationPresenter
from gui.features.input.InputImportPresenter import InputImportPresenter


class InputScreenPresenter:
    """Coordinates the input screen.

    Each concern lives in its own collaborator — file import
    (InputImportPresenter), the scheduler run lifecycle (GenerationPresenter),
    and constraint settings (ConstraintsPresenter). This class owns only the
    state that combines more than one collaborator: program-selection
    validation and Generate-button gating (which depends on import state,
    date validity, and program selection together).
    """

    # Connects the UI to the controller and wires up the import/generation/constraints collaborators
    def __init__(self, view, controller, router, output_screen_name: str) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._output_screen_name = output_screen_name

        self._import = InputImportPresenter(view, controller, on_loaded=self.refresh_generate_button)
        self._generation = GenerationPresenter(view, controller, router, output_screen_name)
        self._constraints = ConstraintsPresenter(view, controller, on_changed=self.refresh_generate_button)

        # Listen for signals coming from the background controller (like when a search finishes)
        self._controller.schedule_found.connect(self.on_schedule_found)
        self._controller.progress_updated.connect(self.on_progress_updated)
        self._controller.search_finished.connect(self.on_search_finished)
        self._controller.error_occurred.connect(self.on_error_occurred)
        self._controller.early_results_ready.connect(self.on_early_results_ready)

    # ── compatibility accessors ──────────────────────────────────────────────
    # Existing unit tests construct this presenter directly and poke its
    # private import-state flags. These forward to InputImportPresenter, the
    # real owner of that state, so the contract this presenter already had
    # keeps working.
    @property
    def _courses_loaded(self) -> bool:
        return self._import.courses_loaded

    @_courses_loaded.setter
    def _courses_loaded(self, value: bool) -> None:
        self._import.courses_loaded = value

    @property
    def _periods_loaded(self) -> bool:
        return self._import.periods_loaded

    @_periods_loaded.setter
    def _periods_loaded(self, value: bool) -> None:
        self._import.periods_loaded = value

    # ── Generate-button gating (combines import + date-validity + programs) ─
    # Checks if all required files are loaded and updates the "Generate" button's state accordingly
    def refresh_generate_button(self) -> None:
        missing = []
        if not self._import.courses_loaded:
            missing.append("courses file")
        if not self._import.periods_loaded:
            missing.append("periods file")

        date_valid = True
        if hasattr(self._view, "is_period_range_valid"):
            date_valid = self._view.is_period_range_valid()

        tooltip = ""
        if missing:
            tooltip = "Please load: " + " and ".join(missing) + " to continue."
        elif not date_valid:
            tooltip = "Fix the exam period dates (end is before start) to continue."

        self._view.set_generate_button_state(bool(len(missing) == 0 and date_valid), tooltip)
        if date_valid:
            self._view.set_validation_message("")
        else:
            self._view.set_validation_message(
                "Exam period end date is before the start date."
            )
        self.validate_programs()

    # Determines if the user wants to completely replace or update existing data
    def selected_mode(self) -> ImportMode:
        return ImportMode.REPLACE if self._view.is_replace_mode_selected() else ImportMode.UPDATE

    # ── import, delegated to InputImportPresenter ────────────────────────────
    # Triggered when the user clicks the "Load Courses" button in the UI
    def on_load_courses_clicked(self) -> None:
        self.on_load_courses(self.selected_mode())

    # Triggered when the user clicks the "Load Periods" button in the UI
    def on_load_periods_clicked(self) -> None:
        self.on_load_periods(self.selected_mode())

    def on_load_courses(self, mode: ImportMode) -> None:
        self._import.on_load_courses(mode)

    def on_load_periods(self, mode: ImportMode) -> None:
        self._import.on_load_periods(mode)

    # ── generation, delegated to GenerationPresenter ─────────────────────────
    def on_generate_clicked(self) -> None:
        self._generation.on_generate_clicked(
            self._collect_selected_program_ids(),
            self.validate_programs,
            self._view.show_program_selection_error,
        )

    def on_cancel_clicked(self) -> None:
        self._generation.on_cancel_clicked()

    def on_schedule_found(self, dto) -> None:
        self._generation.on_schedule_found(dto)

    def on_progress_updated(self, count: int) -> None:
        self._generation.on_progress_updated(count)

    def on_early_results_ready(self) -> None:
        self._generation.on_early_results_ready()

    def on_search_finished(self) -> None:
        self._generation.on_search_finished()

    def on_error_occurred(self, message: str) -> None:
        self._generation.on_error_occurred(message)

    # Navigate to the results screen
    def on_view_results_clicked(self) -> None:
        self._router.show(self._output_screen_name)

    # ── constraints, delegated to ConstraintsPresenter ───────────────────────
    def on_settings_clicked(self) -> None:
        self._constraints.on_settings_clicked()

    def on_constraints_saved(self, updated_vms: list) -> None:
        self._constraints.on_constraints_saved(updated_vms)

    # ── screen lifecycle ──────────────────────────────────────────────────────
    # Ensures the generate button is in the right state when entering the screen
    def on_enter(self) -> None:
        self.refresh_generate_button()

    # ── program selection (shared by Generate-gating and generation kickoff) ─
    # Helper: gathers all currently selected program IDs from the UI
    def _collect_selected_program_ids(self) -> List[str]:
        return self._view.selected_program_ids()

    # Checks if the user has selected at least one program
    def validate_programs(self) -> bool:
        if not self._collect_selected_program_ids():
            self._view.set_program_error("Please select at least one study program.")
            return False

        self._view.set_program_error("")
        return True
