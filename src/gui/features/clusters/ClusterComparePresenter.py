"""Presentation logic for comparing two families' representatives."""
from __future__ import annotations


class ClusterComparePresenter:
    """Loads two representatives and renders them side by side with diffs flagged."""

    def __init__(self, view, controller, router) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._cluster_a = 0
        self._cluster_b = 1

    def set_pair(self, cluster_a: int, cluster_b: int) -> None:
        self._cluster_a = cluster_a
        self._cluster_b = cluster_b

    def on_enter(self) -> None:
        try:
            comparison = self._controller.get_cluster_comparison(
                self._cluster_a, self._cluster_b
            )
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "compare_clusters", "screen": "cluster_compare"}
            )
            self._view.show_message(f"Could not compare clusters: {message}")
            return

        periods = self._available_periods()
        self._view.set_periods(periods)
        self._view.render_comparison(comparison)

    def on_leave(self) -> None:
        pass

    def on_back(self) -> None:
        self._router.back()

    def _available_periods(self):
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []
