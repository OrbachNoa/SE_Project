"""Presentation logic for the shared calendar overlay screen.

Merges two representative schedules and classifies each exam item as
'family_a' (unique to the left family), 'family_b' (unique to the right
family), or 'mutual' (same course+date slot present in both).
"""
from __future__ import annotations

from typing import List, Tuple

from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


class ClusterCalendarOverlayPresenter:
    """Drives the overlay calendar view for a pair of cluster representatives."""

    def __init__(self, view, controller, cluster_controller, router) -> None:
        self._view = view
        self._controller = controller
        self._cluster_controller = cluster_controller
        self._router = router
        self._cluster_a: int = 0
        self._cluster_b: int = 1

    # ── public API ────────────────────────────────────────────────────────

    def set_pair(self, cluster_a: int, cluster_b: int) -> None:
        self._cluster_a = cluster_a
        self._cluster_b = cluster_b

    def on_enter(self) -> None:
        try:
            comparison = self._cluster_controller.get_cluster_comparison(
                self._cluster_a, self._cluster_b
            )
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "overlay_compare", "screen": "cluster_overlay"}
            )
            self._view.show_message(f"Could not load overlay: {message}")
            return

        periods = self._available_periods()
        self._view.set_periods(periods)

        # Build the merged annotated item list.
        merged = self._merge(
            comparison.left_schedule.items,
            comparison.right_schedule.items,
        )

        self._view.set_titles(comparison.left_title, comparison.right_title)
        self._view.render_overlay(merged)

    def on_leave(self) -> None:
        pass

    def on_back(self) -> None:
        self._router.back()

    # ── internal helpers ──────────────────────────────────────────────────

    def _available_periods(self):
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []

    @staticmethod
    def _merge(
        items_a: List[ScheduleItemViewModel],
        items_b: List[ScheduleItemViewModel],
    ) -> List[Tuple[ScheduleItemViewModel, str]]:
        """Classify and merge two sets of schedule items.

        A slot is considered *mutual* when both schedules contain an exam for
        the same course (by title) on the same date.  Everything else is
        unique to whichever family placed it.

        The merge is built so that mutual items appear only once (representing
        both), while unique items from each family appear individually.
        """
        # Build a lookup: (date, title) -> item for each family
        key_a = {(item.date, item.title): item for item in items_a}
        key_b = {(item.date, item.title): item for item in items_b}

        mutual_keys = set(key_a.keys()) & set(key_b.keys())

        result: List[Tuple[ScheduleItemViewModel, str]] = []

        # Mutual items — appear once, labelled "mutual"
        for k in sorted(mutual_keys):
            result.append((key_a[k], "mutual"))

        # Items unique to Family A
        for k in sorted(set(key_a.keys()) - mutual_keys):
            result.append((key_a[k], "family_a"))

        # Items unique to Family B
        for k in sorted(set(key_b.keys()) - mutual_keys):
            result.append((key_b[k], "family_b"))

        return result
