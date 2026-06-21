"""Presentation logic for the cluster overview screen.

On entry it computes the clustering with an automatically chosen K and renders one
card per family. The user can change K and press Apply to re-cluster cheaply (the
feature matrix is cached, so only the partition step re-runs), open a family, or
select two families to compare.
"""
from __future__ import annotations

from typing import List, Optional


class ClusterOverviewPresenter:
    """Computes clusters, renders cards, and coordinates navigation/comparison."""

    def __init__(self, view, controller, router, detail_screen, compare_screen) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._detail = detail_screen
        self._compare = compare_screen

        self._compare_selection: List[int] = []

    # Entry point: compute clusters with automatic K and show the cards.
    def on_enter(self) -> None:
        self._compute(k=None, recompute=False)

    def on_leave(self) -> None:
        pass

    # User changed K and pressed Apply — re-cluster without re-fitting the engine.
    def on_apply_k(self, k: int) -> None:
        if k <= 0:
            self._view.show_message("K must be a positive integer.")
            return
        self._compute(k=k, recompute=True)

    # User typed a free-text request and pressed Apply request.
    def on_apply_request(self, text: str) -> None:
        self._compare_selection = []
        self._view.set_busy(True)
        try:
            cards = self._controller.cluster_from_request(text)
            interpretation = self._controller.get_cluster_interpretation()
        except Exception as error:
            self._view.set_busy(False)
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.set_interpretation("")
            self._view.show_message(f"Could not apply request: {error}")
            return

        self._view.set_busy(False)
        if not cards:
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message("No schedules to cluster yet. Generate schedules first.")
            return

        active_k = self._controller.get_active_k()
        self._view.set_k_value(active_k)
        self._view.set_summary(f"{active_k} families")
        self._view.set_interpretation(interpretation)
        self._view.render_cards(cards)
        self._view.set_compare_enabled(False)

    def on_open_cluster(self, cluster_id: int) -> None:
        self._detail.enter_cluster(cluster_id)
        self._router.show(self._view.detail_screen_name())

    def on_compare_toggled(self, cluster_id: int, selected: bool) -> None:
        if selected:
            self._compare_selection.append(cluster_id)
            # Keep at most two selected; drop the oldest if a third is picked.
            if len(self._compare_selection) > 2:
                dropped = self._compare_selection.pop(0)
                self._view.uncheck_card(dropped)
        elif cluster_id in self._compare_selection:
            self._compare_selection.remove(cluster_id)
        self._view.set_compare_enabled(len(self._compare_selection) == 2)

    def on_compare(self) -> None:
        if len(self._compare_selection) != 2:
            return
        a, b = self._compare_selection[0], self._compare_selection[1]
        self._compare.set_pair(a, b)
        self._router.show(self._view.compare_screen_name())

    def on_back(self) -> None:
        self._router.back()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _compute(self, k: Optional[int], recompute: bool) -> None:
        self._compare_selection = []
        try:
            if recompute:
                cards = self._controller.recompute_clusters(k)
            else:
                cards = self._controller.compute_clusters(k)
        except Exception as error:  # generation may not have produced results yet
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message(f"Could not compute clusters: {error}")
            return

        if not cards:
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message(
                "No schedules to cluster yet. Generate schedules first."
            )
            return

        active_k = self._controller.get_active_k()
        self._view.set_k_value(active_k)
        self._view.set_summary(f"{active_k} families")
        self._view.set_interpretation("")  # automatic grouping has no custom request
        self._view.render_cards(cards)
        self._view.set_compare_enabled(False)
