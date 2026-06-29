"""Presentation logic for browsing the schedules inside one family."""
from __future__ import annotations

from gui.common.ScheduleExportMixin import ScheduleExportMixin
from src.application.errors.ApplicationErrors import ApplicationError


class ClusterDetailPresenter(ScheduleExportMixin):
    """Pages through a family's schedules and exports the chosen one."""

    def __init__(self, view, controller, router) -> None:
        self._view = view
        self._controller = controller
        self._router = router

        self._cluster_id = 0
        self._index = 0
        self._size = 0

        # True only while this screen is the one currently visible. Guards
        # _on_search_finished so a regeneration that finishes after the user
        # has left this screen doesn't pop a stale notice.
        self._is_active = False
        self._update_notice_shown = False
        if hasattr(self._controller, "search_finished"):
            self._controller.search_finished.connect(self._on_search_finished)

    # Called by the overview screen before navigating here.
    def set_cluster(self, cluster_id: int) -> None:
        self._cluster_id = cluster_id
        self._index = 0

    def _handle_error(self, error: Exception, context: dict, user_prefix: str) -> None:
        message = self._controller.map_error(error, context)
        self._view.show_message(f"{user_prefix}{message}")
        self._router.back()

    def on_enter(self) -> None:
        self._is_active = True
        self._update_notice_shown = False
        try:
            self._size = self._controller.get_cluster_size(self._cluster_id)
            if self._size == 0:
                self._view.show_message("The clustering session has expired. \nRedirecting to overview to recompute clusters.")
                self._router.back()
                return
            self._view.set_periods(self._available_periods())
        except Exception as error:
            self._size = 0
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            self._handle_error(error, {"operation": "open_cluster", "screen": "cluster_detail"}, "Could not open this family: ")
            return
        self._show_current()

    def on_leave(self) -> None:
        self._is_active = False

    def _on_search_finished(self) -> None:
        """A new generation run finished while this family was open.

        The cached clustering session this screen is browsing has just been
        invalidated (AppController._invalidate_clustering, fired from
        _handle_search_finished). Tell the user once, but don't force them
        off the screen or touch _cluster_id/_index -- they may still want to
        finish looking at the family they have open.
        """
        if not self._is_active or self._update_notice_shown:
            return
        self._update_notice_shown = True
        self._view.show_message(
            "New results have finished generating. \nGo back to the overview to see the updated families."
        )
        self._router.back()

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

    # ── export hooks for ScheduleExportMixin ─────────────────────────────────
    def _export_has_content(self) -> bool:
        return self._size != 0

    def _export_read_schedule(self):
        return self._controller.get_cluster_schedule_view(self._cluster_id, self._index)

    def _export_filename(self, ext: str) -> str:
        return f"family_{self._cluster_id + 1}_schedule_{self._index + 1}.{ext}"

    def _export_pdf_view(self, schedule_view) -> None:
        self._view.export_schedule_pdf(schedule_view, self._index)

    def _export_save_txt(self, path: str) -> None:
        self._controller.save_cluster_schedule(self._cluster_id, self._index, path)

    def _export_save_excel(self, path: str) -> None:
        self._controller.save_cluster_schedule_excel(self._cluster_id, self._index, path)

    def _export_nothing(self, message: str) -> None:
        self._view.show_message(message)

    def _export_read_error(self, error: Exception, fmt: str) -> None:
        self._handle_error(
            error,
            {"operation": "read_schedule", "screen": "cluster_detail", "export_format": fmt},
            "Could not read schedule: ",
        )

    def _export_save_error(self, error: Exception, fmt: str, path: str) -> None:
        self._handle_error(
            error,
            {"operation": "save_schedule", "screen": "cluster_detail", "export_format": fmt, "path": path},
            "Export failed.\n",
        )

    def _export_saved(self, path: str) -> None:
        self._view.show_message(f"Saved to:\n{path}")

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

    # ── helpers ──────────────────────────────────────────────────────────────

    def _show_current(self) -> None:
        if self._size == 0:
            self._view.set_title(f"Family {self._cluster_id + 1} — empty")
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            self._router.back()
            return
        try:
            schedule_vm = self._controller.get_cluster_schedule_view(self._cluster_id, self._index)
        except ApplicationError:
            # Session expired — user already saw the notice from _on_search_finished.
            # Freeze the view in place; don't kick them back.
            self._view.clear_calendar()
            self._view.set_nav_state(False, False)
            return
        except Exception as error:
            self._view.clear_calendar()
            self._view.set_nav_state(self._index > 0, self._index < self._size - 1)
            self._handle_error(error, {"operation": "read_schedule", "screen": "cluster_detail"}, "Could not load schedule: ")
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
            scores = self._controller.get_cluster_schedule_scores(self._cluster_id, self._index)
        except Exception as error:
            self._handle_error(error, {"operation": "read_schedule", "screen": "cluster_detail"}, "Could not load schedule metrics: ")
            return

        if not scores:
            self._view.show_message("No metrics available for this schedule.")
            return

        from src.logic.clustering import CriterionDisplay
        from src.logic.clustering.ClusteringScorer import EXTENDED_CRITERIA

        summary = []
        for name in EXTENDED_CRITERIA:
            val = scores.get(name, 0.0)
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
