"""Presentation logic for the input screen."""
from __future__ import annotations

from typing import List

from src.application.ImportBoundary import ImportMode


class InputScreenPresenter:
    """Coordinates file import, validation, scheduler lifecycle, and navigation."""

    def __init__(self, view, controller, router, output_screen_name: str) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._output_screen_name = output_screen_name

        self._courses_loaded = False
        self._periods_loaded = False
        self._last_count = 0
        self._already_navigated = False

        self._controller.schedule_found.connect(self.on_schedule_found)
        self._controller.progress_updated.connect(self.on_progress_updated)
        self._controller.search_finished.connect(self.on_search_finished)
        self._controller.error_occurred.connect(self.on_error_occurred)
        self._controller.early_results_ready.connect(self.on_early_results_ready)

    def refresh_generate_button(self) -> None:
        missing = []
        if not self._courses_loaded:
            missing.append("courses file")
        if not self._periods_loaded:
            missing.append("periods file")

        tooltip = ""
        if missing:
            tooltip = "Please load: " + " and ".join(missing) + " to continue."

        self._view.set_generate_button_state(len(missing) == 0, tooltip)
        self._view.set_validation_message("")
        self.validate_programs()

    def selected_mode(self) -> ImportMode:
        return ImportMode.REPLACE if self._view.is_replace_mode_selected() else ImportMode.UPDATE

    def on_load_courses_clicked(self) -> None:
        self.on_load_courses(self.selected_mode())

    def on_load_periods_clicked(self) -> None:
        self.on_load_periods(self.selected_mode())

    def on_load_courses(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select courses file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "courses", mode)
        if not self._handle_import_result(result, "courses"):
            return

        self._courses_loaded = True
        self._view.mark_courses_loaded(result.loaded_count)
        self.refresh_generate_button()

        courses = self._controller.get_loaded_courses()
        mapper = self._controller.get_mapper()
        if courses and mapper is not None:
            self._view.render_courses(mapper.to_program_courses_vm(courses))

    def on_load_periods(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select periods file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "periods", mode)
        if not self._handle_import_result(result, "periods"):
            return

        self._periods_loaded = True
        self._view.mark_periods_loaded(result.loaded_count)
        self.refresh_generate_button()

        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if not periods or mapper is None:
            return

        period_vms = mapper.to_period_edit_vms(periods)
        if period_vms:
            self._view.show_period_editor(period_vms)

    def on_generate_clicked(self) -> None:
        if not self.validate_programs():
            return

        self._already_navigated = False
        self._set_running_mode(True)
        self._controller.generate_schedules(self._collect_selected_program_ids())

    def on_cancel_clicked(self) -> None:
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._view.set_progress_text("")

    def on_view_results_clicked(self) -> None:
        self._router.show(self._output_screen_name)

    def on_constraints_saved(self, updated_vms: list) -> None:
        self._controller.update_exam_periods(updated_vms)
        self.refresh_generate_button()

    def on_schedule_found(self, dto) -> None:
        pass

    def on_progress_updated(self, count: int) -> None:
        self._last_count = count
        suffix = "s" if count != 1 else ""
        self._view.set_progress_text(f"Found {count} schedule{suffix} so far...")

    def on_early_results_ready(self) -> None:
        self._navigate_to_output()

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

    def on_error_occurred(self, message: str) -> None:
        self._set_running_mode(False)
        self._view.show_scheduler_error(message)

    def on_enter(self) -> None:
        self.refresh_generate_button()

    def _collect_selected_program_ids(self) -> List[str]:
        return self._view.selected_program_ids()

    def validate_programs(self) -> bool:
        if not self._collect_selected_program_ids():
            self._view.set_program_error("Please select at least one study program.")
            return False

        self._view.set_program_error("")
        return True

    def _set_running_mode(self, running: bool) -> None:
        if running:
            self._last_count = 0
            self._view.set_running_mode(True, "Initialising scheduler...")
            self._view.set_view_results_visible(False)
        else:
            self._view.set_running_mode(False, "")

    def _navigate_to_output(self) -> None:
        if self._already_navigated:
            return

        self._already_navigated = True
        self._view.set_view_results_visible(True)
        self._router.show(self._output_screen_name)

    def _result_count(self) -> int:
        try:
            info = self._controller.get_page_info()
            return int(info.get("total_count", 0))
        except Exception:
            return self._last_count

    def _handle_import_result(self, result, data_label: str) -> bool:
        if result.success:
            return True

        detail = "\n".join(result.errors) if result.errors else "Unknown error."
        self._view.show_import_error(data_label, detail)
        return False
