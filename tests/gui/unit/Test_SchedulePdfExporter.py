"""Unit tests for the PDF export error path.

The HTML build / Qt-printing step lives entirely in the view layer, outside
any Presenter try/except, so a failure there used to show the raw exception
in its own QMessageBox. It now takes an optional `on_error(exc, path)`
callback (wired to the Presenter's map_error) and only ever displays what
that callback returns — never the exception itself.

Conventions:
- Each test carries a unique TC-PDF-NNN identifier in the comment block above
  its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections. Mock
  configuration that depends on an active patch() lives inside the Act
  section, since the mock objects only exist once the patch is applied.
- No conftest fixture models a ScheduleViewModel, so _make_view() builds one
  locally.
"""
from unittest.mock import MagicMock, patch

from gui.features.output.widgets.SchedulePdfExporter import export_schedule_pdf
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel


def _make_view():
    return ScheduleViewModel(
        items=[ScheduleItemViewModel(date="2026-06-01", title="A", subtitle="B", tooltip="C")],
        current_index=0,
        total=1,
    )


# ===========================================================================
# TC-PDF-001: a write failure is shown via the on_error callback's message,
# not the raw exception — covers PermissionError specifically.
# ===========================================================================
def test_pdf_exporter_export_failure_uses_on_error_callback_message():
    # Arrange
    view = _make_view()
    on_error = MagicMock(return_value="The file could not be written. Please close it and try again.")
    error = PermissionError(13, "denied", "out.pdf")

    # Act
    # Mocks are configured inline because they only exist once patch() is active.
    with patch("gui.features.output.widgets.SchedulePdfExporter.QFileDialog") as mock_dialog, \
         patch("gui.features.output.widgets.SchedulePdfExporter.QMessageBox") as mock_box, \
         patch("gui.features.output.widgets.SchedulePdfExporter._write_html_to_pdf") as mock_write:
        mock_dialog.getSaveFileName.return_value = ("out.pdf", "PDF files (*.pdf)")
        mock_write.side_effect = error
        export_schedule_pdf(view, 0, parent=None, on_error=on_error)

    # Assert
    assert on_error.call_count == 1
    assert on_error.call_args[0][0] is error
    assert on_error.call_args[0][1] == "out.pdf"
    assert mock_box.critical.call_count == 1
    message = mock_box.critical.call_args[0][2]
    assert message == "The file could not be written. Please close it and try again."
    assert "PermissionError" not in message
    assert "Traceback" not in message


# ===========================================================================
# TC-PDF-002: without an on_error callback, the fallback message is still
# safe — no raw exception text, no traceback.
# ===========================================================================
def test_pdf_exporter_export_failure_without_callback_is_safe():
    # Arrange
    view = _make_view()

    # Act
    with patch("gui.features.output.widgets.SchedulePdfExporter.QFileDialog") as mock_dialog, \
         patch("gui.features.output.widgets.SchedulePdfExporter.QMessageBox") as mock_box, \
         patch("gui.features.output.widgets.SchedulePdfExporter._write_html_to_pdf") as mock_write:
        mock_dialog.getSaveFileName.return_value = ("out.pdf", "PDF files (*.pdf)")
        mock_write.side_effect = OSError("disk full: a very specific internal detail")
        export_schedule_pdf(view, 0, parent=None)

    # Assert
    assert mock_box.critical.call_count == 1
    message = mock_box.critical.call_args[0][2]
    assert "disk full" not in message
    assert "OSError" not in message
    assert "Traceback" not in message


# ===========================================================================
# TC-PDF-003: a successful export is unaffected by the new parameter — still
# shows the success dialog, never touches on_error.
# ===========================================================================
def test_pdf_exporter_export_success_does_not_call_on_error():
    # Arrange
    view = _make_view()
    on_error = MagicMock()

    # Act
    with patch("gui.features.output.widgets.SchedulePdfExporter.QFileDialog") as mock_dialog, \
         patch("gui.features.output.widgets.SchedulePdfExporter.QMessageBox") as mock_box, \
         patch("gui.features.output.widgets.SchedulePdfExporter._write_html_to_pdf"):
        mock_dialog.getSaveFileName.return_value = ("out.pdf", "PDF files (*.pdf)")
        export_schedule_pdf(view, 0, parent=None, on_error=on_error)

    # Assert
    assert on_error.call_count == 0
    assert mock_box.information.call_count == 1
    assert mock_box.critical.call_count == 0
