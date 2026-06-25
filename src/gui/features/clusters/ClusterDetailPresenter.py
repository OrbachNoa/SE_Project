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
        try:
            self._size = self._controller.get_cluster_size(self._cluster_id)
            self._view.set_periods(self._available_periods())
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "open_cluster", "screen": "cluster_detail"}
            )
            self._size = 0
            self._view.show_message(f"Could not open this family: {message}")
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            return
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
            # "Export failed" rather than "Could not save: <message>" — the
            # mapped message already says the file "could not be written",
            # so a "Could not save" prefix would just restate that.
            self._view.show_message(f"Export failed.\n{message}")

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
            self._view.show_message(f"Export failed.\n{message}")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _show_current(self) -> None:
        if self._size == 0:
            self._view.set_title(f"Family {self._cluster_id + 1} — empty")
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            return
        try:
            schedule_vm = self._controller.get_cluster_schedule_view(self._cluster_id, self._index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "cluster_detail"}
            )
            self._view.show_message(f"Could not load schedule: {message}")
            self._view.clear_calendar()
            self._view.set_nav_state(self._index > 0, self._index < self._size - 1)
            return
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

    def on_show_metrics(self) -> None:
        if self._size == 0:
            return
        try:
            schedule_vm = self._controller.get_cluster_schedule_view(self._cluster_id, self._index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "cluster_detail"}
            )
            self._view.show_message(f"Could not load schedule metrics: {message}")
            return

        if not schedule_vm or not schedule_vm.scores:
            self._view.show_message("No metrics available for this schedule.")
            return

        from src.logic.clustering import CriterionDisplay
        from src.logic.clustering.ClusteringScorer import EXTENDED_CRITERIA

        summary = []
        for name in EXTENDED_CRITERIA:
            val = schedule_vm.scores.get(name, 0.0)
            summary.append((
                name,
                CriterionDisplay.label(name),
                CriterionDisplay.display_value(name, val)
            ))

        from gui.features.clusters.widgets.AllMetricsDialog import AllMetricsDialog
        dialog = AllMetricsDialog(
            title=f"Schedule {self._index + 1}",
            summary=summary,
            min_max={},
            defining_criterion="",
            parent=self._view.window()
        )
        dialog.exec()
