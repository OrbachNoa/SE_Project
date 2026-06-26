"""Shared fixtures for GUI tests only — this conftest.py applies to every
test under tests/gui/ (unit and integration) and nowhere else, since
pytest scopes a conftest.py to its own directory subtree.
"""
import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def _block_real_qmessagebox():
    """Safety net: no GUI test may pop a real, blocking QMessageBox.

    This patches QMessageBox.information/warning/critical/question with
    harmless mocks for every test under tests/gui/, so a call path a test
    forgot to patch is silently absorbed instead of opening a real modal
    dialog that blocks an unattended run.

    A test that needs to assert a specific dialog call still patches that
    exact method itself (locally, via `with patch(...)` or `@patch(...)`).
    That local patch takes precedence over this fixture for its scope —
    standard nested-mock behaviour — so every existing assertion about
    call counts, arguments, or messages is completely unaffected by this
    fixture; it only catches what nothing else is already covering.
    """
    with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok), \
         patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok), \
         patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok), \
         patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        yield
