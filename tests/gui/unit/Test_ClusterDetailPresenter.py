"""Unit tests for ClusterDetailPresenter's export error handling.

Every export failure routes through controller.map_error (never a raw
f"...{error}"), and map_export_error gives the view-layer PDF exporter a way
back to that same mapper for failures that happen outside any try/except here.

Conventions:
- Each test carries a unique TC-CDP-NNN identifier in the comment block above
  its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- controller and router come from the shared mock_controller / mock_router
  fixtures (tests/conftest.py); the view has no shared fixture, so it is
  built locally by the _presenter() helper below.
"""
from unittest.mock import MagicMock

from src.gui.features.clusters.ClusterDetailPresenter import ClusterDetailPresenter


def _presenter(controller, router):
    view = MagicMock()
    presenter = ClusterDetailPresenter(view, controller, router)
    presenter._size = 1
    return presenter, view


# ===========================================================================
# TC-CDP-001: map_export_error delegates to controller.map_error with the
# cluster_detail/export_pdf context.
# ===========================================================================
def test_cluster_detail_presenter_map_export_error_delegates_to_controller(mock_controller, mock_router):
    # Arrange
    presenter, view = _presenter(mock_controller, mock_router)
    mock_controller.map_error.return_value = "The file could not be written. Please try again."
    error = PermissionError("denied")

    # Act
    message = presenter.map_export_error(error, "out.pdf")

    # Assert
    assert message == "The file could not be written. Please try again."
    call_error, context = mock_controller.map_error.call_args[0]
    assert call_error is error
    assert context["operation"] == "export_pdf"
    assert context["screen"] == "cluster_detail"
    assert context["path"] == "out.pdf"


# ===========================================================================
# TC-CDP-002: on_export_excel shows the mapped message, never a raw
# PermissionError string — there is no separate `except PermissionError`.
# ===========================================================================
def test_cluster_detail_presenter_export_excel_failure_uses_mapped_message(mock_controller, mock_router):
    # Arrange
    presenter, view = _presenter(mock_controller, mock_router)
    view.ask_save_path_excel.return_value = "out.xlsx"
    mock_controller.save_cluster_schedule_excel.side_effect = PermissionError("denied")
    mock_controller.map_error.return_value = "The file could not be written. Please close it and try again."

    # Act
    presenter.on_export_excel()

    # Assert
    assert mock_controller.map_error.call_count == 1
    context = mock_controller.map_error.call_args[0][1]
    assert context["export_format"] == "excel"
    assert context["path"] == "out.xlsx"
    message = view.show_message.call_args[0][0]
    assert "The file could not be written. Please close it and try again." in message
    assert "PermissionError" not in message
    # The mapped message already says the file could not be written, so a
    # "Could not save" prefix would just restate that.
    assert "Could not save" not in message
    assert message.startswith("Export failed.")


# ===========================================================================
# TC-CDP-003: on_enter recovers when get_cluster_size raises (e.g. a stale
# cluster_id after the underlying clustering run changed) — the screen shows
# a mapped message and clears itself instead of letting the exception
# propagate up to the global sys.excepthook.
# ===========================================================================
def test_cluster_detail_presenter_on_enter_recovers_when_get_cluster_size_fails(mock_controller, mock_router):
    # Arrange
    presenter, view = _presenter(mock_controller, mock_router)
    error = IndexError("cluster 3 does not exist (have 2)")
    mock_controller.get_cluster_size.side_effect = error
    mock_controller.map_error.return_value = "Could not open this family. Please try again."

    # Act
    presenter.on_enter()

    # Assert
    assert mock_controller.map_error.call_count == 1
    assert mock_controller.map_error.call_args[0][0] is error
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
def test_cluster_detail_presenter_show_current_recovers_when_read_schedule_fails(mock_controller, mock_router):
    # Arrange
    presenter, view = _presenter(mock_controller, mock_router)
    presenter._size = 3
    presenter._index = 1
    error = RuntimeError("sqlite read failure")
    mock_controller.get_cluster_schedule_view.side_effect = error
    mock_controller.map_error.return_value = "Could not load the schedule. Please try again."

    # Act
    presenter._show_current()

    # Assert
    assert mock_controller.map_error.call_count == 1
    assert mock_controller.map_error.call_args[0][0] is error
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
def test_cluster_detail_presenter_on_next_recovers_when_read_schedule_fails(mock_controller, mock_router):
    # Arrange
    presenter, view = _presenter(mock_controller, mock_router)
    presenter._size = 3
    presenter._index = 0
    mock_controller.get_cluster_schedule_view.side_effect = RuntimeError("sqlite read failure")
    mock_controller.map_error.return_value = "Could not load the schedule. Please try again."

    # Act
    presenter.on_next()

    # Assert
    assert presenter._index == 1
    assert mock_controller.map_error.call_count == 1
    assert view.show_message.call_count == 1
