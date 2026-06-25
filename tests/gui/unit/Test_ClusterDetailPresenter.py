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
