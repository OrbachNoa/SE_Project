import pytest
from unittest.mock import MagicMock
from src.gui.features.input.InputScreenPresenter import InputScreenPresenter
from src.application.ImportBoundary import ImportMode, ImportResult

# ===========================================================================
# TC-ISP-001: test refresh generate button state when both files are missing.
# ===========================================================================
def test_presenter_refresh_generate_button_files_missing(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    # Initially programs are not empty
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.refresh_generate_button()
    
    # Assert
    assert view.set_generate_button_state.call_count == 1
    assert view.set_generate_button_state.call_args[0] == (False, "Please load: courses file and periods file to continue.")

# ===========================================================================
# TC-ISP-002: test refresh generate button state when periods file is missing.
# ===========================================================================
def test_presenter_refresh_generate_button_periods_missing(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    presenter._courses_loaded = True
    
    # Act
    presenter.refresh_generate_button()
    
    # Assert
    assert view.set_generate_button_state.call_count == 1
    assert view.set_generate_button_state.call_args[0] == (False, "Please load: periods file to continue.")

# ===========================================================================
# TC-ISP-003: test refresh generate button state when both files are loaded.
# ===========================================================================
def test_presenter_refresh_generate_button_ready(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    presenter._courses_loaded = True
    presenter._periods_loaded = True
    
    # Act
    presenter.refresh_generate_button()
    
    # Assert
    assert view.set_generate_button_state.call_count == 1
    assert view.set_generate_button_state.call_args[0] == (True, "")

# ===========================================================================
# TC-ISP-004: test program validation fails when no programs are selected.
# ===========================================================================
def test_presenter_validate_programs_empty(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = []
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    res = presenter.validate_programs()
    
    # Assert
    assert res is False
    assert view.set_program_error.call_count == 1
    assert view.set_program_error.call_args[0] == ("Please select at least one study program.",)

# ===========================================================================
# TC-ISP-005: test program validation succeeds when programs are selected.
# ===========================================================================
def test_presenter_validate_programs_success(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    res = presenter.validate_programs()
    
    # Assert
    assert res is True
    assert view.set_program_error.call_count == 1
    assert view.set_program_error.call_args[0] == ("",)

# ===========================================================================
# TC-ISP-006: test generate clicked starts schedule generation.
# ===========================================================================
def test_presenter_on_generate_clicked(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101", "83102"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_generate_clicked()
    
    # Assert
    assert view.set_running_mode.call_count == 1
    assert view.set_running_mode.call_args[0] == (True, "Initialising scheduler...")
    assert mock_controller.generate_schedules.call_count == 1
    assert mock_controller.generate_schedules.call_args[0] == (["83101", "83102"],)

# ===========================================================================
# TC-ISP-007: test load courses handles success.
# ===========================================================================
def test_presenter_on_load_courses_success(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "courses.csv"
    view.is_replace_mode_selected.return_value = True
    
    res = ImportResult(success=True, loaded_count=10, errors=[])
    mock_controller.load_file.return_value = res
    mock_controller.get_loaded_courses.return_value = []
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_load_courses_clicked()
    
    # Assert
    assert mock_controller.load_file.call_count == 1
    assert mock_controller.load_file.call_args[0] == ("courses.csv", "courses", ImportMode.REPLACE)
    assert presenter._courses_loaded is True
    assert view.mark_courses_loaded.call_count == 1
    assert view.mark_courses_loaded.call_args[0] == (10,)

# ===========================================================================
# TC-ISP-008: test load courses handles failure.
# ===========================================================================
def test_presenter_on_load_courses_failure(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "courses.csv"
    view.is_replace_mode_selected.return_value = True
    
    res = ImportResult(success=False, loaded_count=0, errors=["CSV parser error"])
    mock_controller.load_file.return_value = res
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_load_courses_clicked()
    
    # Assert
    assert presenter._courses_loaded is False
    assert view.show_import_error.call_count == 1
    assert view.show_import_error.call_args[0] == ("courses", "CSV parser error")

# ===========================================================================
# TC-ISP-009: test progress label updates for multiple schedules (plural).
# ===========================================================================
def test_presenter_on_progress_updated_plural(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_progress_updated(5)
    
    # Assert
    assert view.set_progress_text.call_count == 1
    assert view.set_progress_text.call_args[0] == ("Found 5 schedules so far...",)

# ===========================================================================
# TC-ISP-010: test progress label updates for one schedule (singular).
# ===========================================================================
def test_presenter_on_progress_updated_singular(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_progress_updated(1)
    
    # Assert
    assert view.set_progress_text.call_count == 1
    assert view.set_progress_text.call_args[0] == ("Found 1 schedule so far...",)

# ===========================================================================
# TC-ISP-011: test early results navigation callback.
# ===========================================================================
def test_presenter_on_early_results_ready(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    
    # Act
    presenter.on_early_results_ready()
    
    # Assert
    assert view.set_view_results_visible.call_count == 1
    assert view.set_view_results_visible.call_args[0] == (True,)
    assert mock_router.show.call_count == 1
    assert mock_router.show.call_args[0] == ("output",)
