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

    def on_export(self) -> None:
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
            self._view.show_message(f"Could not save: {error}")

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
