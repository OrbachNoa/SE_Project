"""Presentation logic for the cluster overview screen.

On entry it computes the clustering with an automatically chosen K and renders one
card per family. The user can change K and press Apply to re-cluster cheaply (the
feature matrix is cached, so only the partition step re-runs), open a family, or
select two families to compare.
"""
from __future__ import annotations

from typing import List, Optional

from src.infrastructure.concurrency.ClusterWorker import ClusterWorker


class ClusterOverviewPresenter:
    """Computes clusters, renders cards, and coordinates navigation/comparison."""

    def __init__(self, view, controller, router, detail_screen, compare_screen) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._detail = detail_screen
        self._compare = compare_screen

        self._compare_selection: List[int] = []
        self._worker: Optional[ClusterWorker] = None
        self._last_request_text: str = ""
        self._last_k: Optional[int] = None

    # Entry point: compute clusters. Reuse the last active K if one exists so
    # the view stays consistent after a generation run invalidates the cache.
    # If entering for the first time (no active clusters), use default automatic K.
    def on_enter(self) -> None:
        if self._controller.has_clusters():
            # Restore last request text in the input field
            if self._last_request_text:
                self._view._request_input.setText(self._last_request_text)
            else:
                self._view._request_input.setText("")
            # Use last active K for consistency
            prev_k = self._controller.get_active_k()
            self._kick_off(k=prev_k or None, recompute=False)
        else:
            self._last_k = None
            self._last_request_text = ""
            self._view._request_input.setText("")
            self._kick_off(k=None, recompute=False)

    def on_leave(self) -> None:
        pass

    # User changed K and pressed Apply — re-cluster without re-fitting the engine.
    def on_apply_k(self, k: int) -> None:
        if k <= 0:
            self._view.show_message("K must be a positive integer.")
            return
        self._last_k = k
        self._kick_off(k=k, recompute=True)

    # User typed a free-text request and pressed Apply request.
    def on_apply_request(self, text: str, k: Optional[int] = None) -> None:
        self._compare_selection = []
        self._view.set_busy(True)
        
        import warnings
        from sklearn.exceptions import ConvergenceWarning

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", category=ConvergenceWarning)
                cards = self._controller.cluster_from_request(text, k)
                interpretation = self._controller.get_cluster_interpretation()
                
                custom_warn = "\n\n".join(list(dict.fromkeys([str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)])))
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

        self._warn_capped_k(k, active_k, custom_warn if custom_warn else None)

        # Save state on success
        self._last_request_text = text
        if k is not None:
            self._last_k = k
        else:
            self._last_k = None

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

    # ── background work ───────────────────────────────────────────────────────

    def _kick_off(self, k: Optional[int], recompute: bool) -> None:
        """Start a ClusterWorker so clustering runs off the GUI thread."""
        self._compare_selection = []

        # fresh=True forces a new sample+fit (on_enter); fresh=False reuses
        # the already-fitted matrix for a cheap K-change (on_apply_k).
        coordinator = self._controller.get_cluster_coordinator(fresh=not recompute)
        if coordinator is None:
            self._view.show_message("No schedules to cluster yet. Generate schedules first.")
            return

        # Only show the spinner when prepare() is actually going to run.
        # If the coordinator is already prepared, the worker will finish
        # near-instantly from the cached matrix — showing the spinner would
        # only produce a distracting flash.
        if not coordinator.is_prepared:
            self._view.set_busy(True)

        self._worker = ClusterWorker(coordinator, k=k)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_finished(self, run) -> None:
        self._view.set_busy(False)
        try:
            # Store the run in the facade (so get_active_k etc. work) and
            # convert to card view models — both are cheap, GUI thread is fine.
            cards = self._controller.cards_from_run(run)
        except Exception as error:
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message(f"Could not render clusters: {error}")
            return

        if not cards:
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message("No schedules to cluster yet. Generate schedules first.")
            return

        active_k = self._controller.get_active_k()
        self._view.set_k_value(active_k)
        self._view.set_summary(f"{active_k} families")
        self._view.set_interpretation("")
        self._view.render_cards(cards)
        self._view.set_compare_enabled(False)

        custom_warn = "\n\n".join(list(dict.fromkeys(self._worker.warnings))) if self._worker and self._worker.warnings else None
        self._warn_capped_k(self._last_k, active_k, custom_warn)

    def _on_worker_failed(self, message: str) -> None:
        self._view.set_busy(False)
        self._view.render_cards([])
        self._view.set_summary("")
        self._view.show_message(f"Could not compute clusters: {message}")

    def _warn_capped_k(self, requested_k: Optional[int], active_k: int, custom_warning: Optional[str] = None) -> None:
        """Alerts the user if the requested cluster count was limited/capped or raised a warning."""
        if (requested_k is not None and active_k < requested_k) or custom_warning:
            if custom_warning:
                msg = (
                    f"Clustering Warning:\n\n{custom_warning}\n\n"
                    f"The engine could not split the schedules into the requested {requested_k} families "
                    f"because they do not have enough distinct score variations."
                )
            else:
                msg = (
                    f"Could only group into {active_k} families.\n\n"
                    f"The generated schedules do not have enough distinct score variations "
                    f"to form {requested_k} separate families."
                )
            self._view.show_message(msg)
