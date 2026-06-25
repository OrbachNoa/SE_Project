"""Presentation logic for browsing the schedules inside one family."""
from __future__ import annotations


class ClusterDetailPresenter:
    """Pages through a family's schedules and exports the chosen one."""

    def __init__(self, view, controller, router) -> None:
        self._view = view
        self._controller = controller
        self._router = router

        self._cluster_id = 0
        self._index = 0
        self._size = 0

    # Called by the overview screen before navigating here.
    def set_cluster(self, cluster_id: int) -> None:
        self._cluster_id = cluster_id
        self._index = 0

    def on_enter(self) -> None:
        self._size = self._controller.get_cluster_size(self._cluster_id)
        self._view.set_periods(self._available_periods())
        self._show_current()

    def on_leave(self) -> None:
        pass

    def on_back(self) -> None:
        self._router.back()

    def on_next(self) -> None:
        if self._index < self._size - 1:
            self._index += 1
            self._show_current()

    def on_prev(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._show_current()

    def on_export_pdf(self) -> None:
        if self._size == 0:
            self._view.show_message("This family has no schedules to export.")
            return
        try:
            schedule_vm = self._controller.get_cluster_schedule_view(self._cluster_id, self._index)
            self._view.export_schedule_pdf(schedule_vm, self._index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "cluster_detail", "export_format": "pdf"}
            )
            self._view.show_message(f"Could not read schedule: {message}")

    def map_export_error(self, error: Exception, path: str) -> str:
        """Map a PDF-writing failure (called by SchedulePdfExporter) to a clean message.

        The HTML/Qt-printing step happens inside the view-layer PDF exporter,
        outside any try/except this presenter runs — this gives it a way back
        to the same controller.map_error used by every other export path.
        """
        return self._controller.map_error(
            error,
            {"operation": "export_pdf", "screen": "cluster_detail", "export_format": "pdf", "path": path},
        )

    def on_export_txt(self) -> None:
        if self._size == 0:
            self._view.show_message("This family has no schedules to export.")
            return
        path = self._view.ask_save_path(
            f"family_{self._cluster_id + 1}_schedule_{self._index + 1}.txt"
        )
        if not path:
            return
        try:
            self._controller.save_cluster_schedule(self._cluster_id, self._index, path)
            self._view.show_message(f"Saved to:\n{path}")
        except Exception as error:
            message = self._controller.map_error(
                error,
                {"operation": "save_schedule", "screen": "cluster_detail", "export_format": "txt", "path": path},
            )
            self._view.show_message(f"Could not save: {message}")

    # Initiates the Excel export process for the current cluster schedule
    def on_export_excel(self) -> None:
        # Check if there is data to export
        if self._size == 0:
            self._view.show_message("This family has no schedules to export.")
            return

        # Prompt the user for the save location
        path = self._view.ask_save_path_excel(
            f"family_{self._cluster_id + 1}_schedule_{self._index + 1}.xlsx"
        )
        if not path:
            return

        try:
            # Call the controller to handle the saving logic
            self._controller.save_cluster_schedule_excel(self._cluster_id, self._index, path)
            self._view.show_message(f"Saved to:\n{path}")
        except Exception as error:
            # PermissionErrorMapper already produces a friendly "file is open
            # elsewhere" message, so there is no separate `except
            # PermissionError` here — one path covers every failure.
            message = self._controller.map_error(
                error,
                {"operation": "save_schedule", "screen": "cluster_detail", "export_format": "excel", "path": path},
            )
            self._view.show_message(f"Could not save Excel schedule: {message}")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _show_current(self) -> None:
        if self._size == 0:
            self._view.set_title(f"Family {self._cluster_id + 1} — empty")
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            return
        schedule_vm = self._controller.get_cluster_schedule_view(self._cluster_id, self._index)
        self._view.set_title(
            f"Family {self._cluster_id + 1} — schedule {self._index + 1} / {self._size}"
        )
        self._view.show_schedule(schedule_vm)
        self._view.set_nav_state(self._index > 0, self._index < self._size - 1)

    def _available_periods(self):
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []
