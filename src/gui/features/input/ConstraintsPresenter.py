"""Owns opening the constraints settings dialog and applying its result.

Split out of InputScreenPresenter (the "constraints" concern).
"""
from __future__ import annotations

from typing import Callable

from gui.features.input.widgets.ConstraintsSettingsDialog import ConstraintsSettingsDialog


class ConstraintsPresenter:
    """Opens the constraints dialog and pushes the result to the controller."""

    def __init__(self, view, controller, on_changed: Callable[[], None]) -> None:
        self._view = view
        self._controller = controller
        self._on_changed = on_changed

    # Triggered when the user clicks the settings button to adjust constraints configurations
    def on_settings_clicked(self) -> None:
        current = self._controller.get_constraints_config()
        dialog = ConstraintsSettingsDialog(
            on_apply=self._apply_constraints_config,
            current_config=current,
            parent=self._view,
        )
        dialog.exec()

    def _apply_constraints_config(self, config) -> None:
        self._controller.set_constraints_config(config)
        mark_dirty = getattr(self._view, "mark_inputs_dirty", None)
        if callable(mark_dirty):
            mark_dirty()
        else:
            self._on_changed()

    # Updates the exam period constraints in the controller
    def on_constraints_saved(self, updated_vms: list) -> None:
        self._controller.update_exam_periods(updated_vms)
        self._on_changed()
