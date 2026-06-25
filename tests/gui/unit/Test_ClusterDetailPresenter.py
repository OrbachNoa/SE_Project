"""Unit tests for ClusterDetailPresenter's export error handling.

Every export failure routes through controller.map_error (never a raw
f"...{error}"), and map_export_error gives the view-layer PDF exporter a way
back to that same mapper for failures that happen outside any try/except here.
"""
from unittest.mock import MagicMock

from src.gui.features.clusters.ClusterDetailPresenter import ClusterDetailPresenter


def _presenter(controller=None):
    view = MagicMock()
    controller = controller or MagicMock()
    router = MagicMock()
    presenter = ClusterDetailPresenter(view, controller, router)
    presenter._size = 1
    return presenter, view, controller


# ===========================================================================
# TC-CDP-001: map_export_error delegates to controller.map_error with the
# cluster_detail/export_pdf context.
# ===========================================================================
def test_map_export_error_delegates_to_controller():
    presenter, view, controller = _presenter()
    controller.map_error.return_value = "The file could not be written. Please try again."
    error = PermissionError("denied")

    message = presenter.map_export_error(error, "out.pdf")

    assert message == "The file could not be written. Please try again."
    call_error, context = controller.map_error.call_args[0]
    assert call_error is error
    assert context["operation"] == "export_pdf"
    assert context["screen"] == "cluster_detail"
    assert context["path"] == "out.pdf"


# ===========================================================================
# TC-CDP-002: on_export_excel shows the mapped message, never a raw
# PermissionError string — there is no separate `except PermissionError`.
# ===========================================================================
def test_on_export_excel_failure_uses_mapped_message():
    presenter, view, controller = _presenter()
    view.ask_save_path_excel.return_value = "out.xlsx"
    controller.save_cluster_schedule_excel.side_effect = PermissionError("denied")
    controller.map_error.return_value = "The file could not be written. Please close it and try again."

    presenter.on_export_excel()

    assert controller.map_error.call_count == 1
    context = controller.map_error.call_args[0][1]
    assert context["export_format"] == "excel"
    assert context["path"] == "out.xlsx"
    message = view.show_message.call_args[0][0]
    assert "The file could not be written. Please close it and try again." in message
    assert "PermissionError" not in message
    # "Export failed." not "Could not save Excel schedule:" — the mapped
    # message already says the file could not be written, so a "save"
    # prefix would just restate that.
    assert "Could not save" not in message
    assert message.startswith("Export failed.")


# ===========================================================================
# TC-CDP-003: on_enter recovers when get_cluster_size raises (e.g. a stale
# cluster_id after the underlying clustering run changed) — the screen shows
# a mapped message and clears itself instead of letting the exception
# propagate up to the global sys.excepthook.
# ===========================================================================
def test_on_enter_recovers_when_get_cluster_size_fails():
    presenter, view, controller = _presenter()
    error = IndexError("cluster 3 does not exist (have 2)")
    controller.get_cluster_size.side_effect = error
    controller.map_error.return_value = "Could not open this family. Please try again."

    presenter.on_enter()

    assert controller.map_error.call_count == 1
    assert controller.map_error.call_args[0][0] is error
    message = view.show_message.call_args[0][0]
    assert "Could not open this family. Please try again." in message
    assert "IndexError" not in message
    view.clear_calendar.assert_called_once()
    view.set_nav_state.assert_called_once_with(False, False)


# ===========================================================================
# TC-CDP-004: _show_current recovers when get_cluster_schedule_view raises
# (e.g. a storage read failure) — the screen shows a mapped message and
# stays navigable instead of crashing.
# ===========================================================================
def test_show_current_recovers_when_read_schedule_fails():
    presenter, view, controller = _presenter()
    presenter._size = 3
    presenter._index = 1
    error = RuntimeError("sqlite read failure")
    controller.get_cluster_schedule_view.side_effect = error
    controller.map_error.return_value = "Could not load the schedule. Please try again."

    presenter._show_current()

    assert controller.map_error.call_count == 1
    assert controller.map_error.call_args[0][0] is error
    message = view.show_message.call_args[0][0]
    assert "Could not load the schedule. Please try again." in message
    assert "RuntimeError" not in message
    view.clear_calendar.assert_called_once()
    view.set_nav_state.assert_called_once_with(True, True)
    view.show_schedule.assert_not_called()


# ===========================================================================
# TC-CDP-005: on_next still routes through the same recoverable path —
# navigating forward into a schedule that fails to load does not crash.
# ===========================================================================
def test_on_next_recovers_when_read_schedule_fails():
    presenter, view, controller = _presenter()
    presenter._size = 3
    presenter._index = 0
    controller.get_cluster_schedule_view.side_effect = RuntimeError("sqlite read failure")
    controller.map_error.return_value = "Could not load the schedule. Please try again."

    presenter.on_next()

    assert presenter._index == 1
    assert controller.map_error.call_count == 1
    assert view.show_message.call_count == 1
