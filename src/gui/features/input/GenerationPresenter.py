"""Owns the scheduler run lifecycle: start/cancel generation and react to
controller signals (progress, early results, search finished, errors).

Split out of InputScreenPresenter (the "generation" concern). Program
selection validation and Generate-button gating stay with the coordinator
since they combine state from multiple collaborators (import + date-validity +
program selection); this class is handed the selected program ids and a
validate/show-error callback at call time instead of owning that logic itself.
"""
from __future__ import annotations

from typing import Callable, List


class GenerationPresenter:
    """Starts/cancels schedule generation and reacts to scheduler signals."""

    def __init__(self, view, controller, router, output_screen_name: str) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._output_screen_name = output_screen_name

        self._last_count = 0
        self._already_navigated = False

    # Starts the scheduling process in the background controller
    def on_generate_clicked(
        self,
        selected_program_ids: List[str],
        validate: Callable[[], bool],
        show_program_error: Callable[[str], None],
    ) -> None:
        if not validate():
            show_program_error(
                "Please select at least one study program before generating a schedule."
            )
            return

        self._already_navigated = False
        self._set_running_mode(True)
        self._controller.generate_schedules(selected_program_ids)

    # Stops the scheduling process if the user clicks cancel
    def on_cancel_clicked(self) -> None:
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._view.set_progress_text("")
        if hasattr(self._view, "mark_inputs_dirty"):
            self._view.mark_inputs_dirty()

    def on_schedule_found(self, dto) -> None:
        pass

    # Updates the progress label while the scheduler is running
    def on_progress_updated(self, count: int) -> None:
        self._last_count = count
        suffix = "s" if count != 1 else ""
        self._view.set_progress_text(f"Found {count} schedule{suffix} so far...")

    # Automatically switches to the output screen as soon as valid results are ready
    def on_early_results_ready(self) -> None:
        self._navigate_to_output()

    # Handles what happens when the scheduling search is fully finished
    def on_search_finished(self) -> None:
        self._set_running_mode(False)
        if self._already_navigated:
            return

        if self._result_count() > 0:
            self._navigate_to_output()
        else:
            self._view.set_validation_message(
                "No valid schedules found. Try adjusting programs or exam dates."
            )

    # Shows an error message if something went wrong during scheduling
    def on_error_occurred(self, message: str) -> None:
        self._set_running_mode(False)
        self._view.show_scheduler_error(message)

    # Updates UI elements based on whether the scheduler is currently "running" or "idle"
    def _set_running_mode(self, running: bool) -> None:
        if running:
            self._last_count = 0
            self._view.set_running_mode(True, "Initialising scheduler...")
            self._view.set_view_results_visible(False)
        else:
            self._view.set_running_mode(False, "")

    # Navigates to the output screen only once
    def _navigate_to_output(self) -> None:
        if self._already_navigated:
            return

        self._already_navigated = True
        self._view.set_view_results_visible(True)
        self._router.show(self._output_screen_name)

    # Gets the total number of schedules found so far from the controller
    def _result_count(self) -> int:
        try:
            info = self._controller.get_page_info()
            return int(info.get("total_count", 0))
        except Exception as error:
            # A transient read glitch during polling shouldn't interrupt an
            # active generation run, so we keep showing the last known count —
            # but still log the technical detail (via the same mapper as every
            # other failure) so a systematic problem isn't entirely silent.
            self._controller.map_error(error, {"operation": "poll_progress", "screen": "input"})
            return self._last_count
