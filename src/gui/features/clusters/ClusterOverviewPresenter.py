"""Presentation logic for the cluster overview screen.

On entry it computes the clustering with an automatically chosen K and renders one
card per family. The user can change K and press Apply to re-cluster cheaply (the
feature matrix is cached, so only the partition step re-runs), open a family, or
select two families to compare.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from src.logic.clustering.CriterionDisplay import label as criterion_label

if TYPE_CHECKING:
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
        self._pending_request_text: str = ""
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
        self._kick_off(k=k, recompute=True)

    # User typed a free-text request and pressed Apply request.
    def on_apply_request(self, text: str, k: Optional[int] = None) -> None:
        # Prevent a second concurrent worker if one is already running.
        if self._worker is not None and self._worker.isRunning():
            return
        if not (text or "").strip():
            self._controller.invalidate_clustering()
            self._kick_off(k=None, recompute=False)
            return
        self._compare_selection = []
        self._pending_request_text = text
        self._view.set_busy(True)
        from src.infrastructure.concurrency.ClusterRequestWorker import ClusterRequestWorker
        self._worker = ClusterRequestWorker(self._controller, text, k)
        self._worker.finished.connect(self._on_request_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

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
        # Imported lazily: ClusterWorker pulls in ClusteringCoordinator ->
        # ClusteringService -> scikit-learn/scipy/pandas (~2.3s to import).
        # Importing it at module level would force every app launch to pay
        # that cost building this screen, even for sessions that never open
        # clustering at all.
        from src.infrastructure.concurrency.ClusterWorker import ClusterWorker

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

    def _on_request_worker_finished(self, bundle) -> None:
        """Handler for ClusterRequestWorker.finished — commit + render."""
        cards = self._controller.commit_request_run(bundle)
        self._finish_render(bundle.run, cards)
        self._last_request_text = self._pending_request_text
        self._last_k = bundle.run.result.k

    def _on_worker_finished(self, run) -> None:
        """Handler for ClusterWorker.finished (on_enter / on_apply_k path)."""
        try:
            cards = self._controller.cards_from_run(run)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "render_cluster_cards", "screen": "clusters"}
            )
            self._view.set_busy(False)
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message(f"Could not render clusters: {message}")
            return
        self._finish_render(run, cards)

    def _finish_render(self, run, cards) -> None:
        """Shared final-render step used by both worker-finished handlers."""
        self._view.set_busy(False)
        if not cards:
            self._view.render_cards([])
            self._view.set_summary("")
            self._view.show_message("No schedules to cluster yet. Generate schedules first.")
            return

        active_k = self._controller.get_active_k()
        self._view.set_k_value(active_k)
        self._view.set_summary(f"{active_k} families")

        parts = []
        interp = self._controller.get_cluster_interpretation()
        if interp:
            parts.append(interp)
        if run.result.requested_k and run.result.requested_k != active_k:
            parts.append(
                f"Note: only {active_k} families could be formed — "
                "the data may not vary enough on these criteria."
            )
        coordinator = self._controller.get_cluster_coordinator()
        if coordinator and coordinator.flat_criteria:
            _flat = coordinator.flat_criteria
            _names = [criterion_label(c) for c in _flat]
            _he = any('א' <= _c <= 'ת' for _c in (parts[0] if parts else ""))
            if len(_names) > 3:
                _suffix = f" ועוד {len(_names) - 3}" if _he else f" +{len(_names) - 3} more"
            else:
                _suffix = ""
            _shown = ", ".join(_names[:3])
            if _he:
                parts.append(f"ללא השפעה (אין שונות): {_shown}{_suffix}")
            else:
                parts.append(f"Unused (no variation): {_shown}{_suffix}")
        self._view.set_interpretation("\n\n".join(parts))

        self._view.render_cards(cards)
        self._view.set_compare_enabled(False)

        custom_warn = (
            "\n\n".join(dict.fromkeys(self._worker.warnings))
            if (self._worker and getattr(self._worker, "warnings", None))
            else None
        )
        self._warn_capped_k(run.result.requested_k or active_k, custom_warn)

    def _on_worker_failed(self, message: str) -> None:
        self._view.set_busy(False)
        self._view.render_cards([])
        self._view.set_summary("")
        self._view.show_message(f"Could not compute clusters: {message}")
        if self._worker is not None:
            self._controller.log_worker_error(self._worker.last_error)

    def _warn_capped_k(self, requested_k: Optional[int], custom_warning: Optional[str] = None) -> None:
        """Alert the user if a ConvergenceWarning fired during clustering."""
        if custom_warning:
            msg = (
                f"Clustering Warning:\n\n{custom_warning}\n\n"
                f"The engine could not split the schedules into the requested {requested_k} families "
                f"because they do not have enough distinct score variations."
            )
            self._view.show_message(msg)
