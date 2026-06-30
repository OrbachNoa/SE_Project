"""Unit tests for InputScreenPresenter — InputScreen's coordination layer.

The presenter mediates between the view (mocked here) and the controller:
it decides when the generate button may be enabled, validates that at
least one program is selected before generation starts, narrows the
available-programs list to whatever the just-loaded courses actually
contain (and does so before the generate button is re-validated against
that narrower list), and turns load/progress/early-results callbacks into
the corresponding view updates.

Conventions:
- Each test carries a unique TC-ISP-NNN identifier in the comment block
  above its definition, numbered sequentially (with lettered variants
  such as 006b/007b/007c for closely related scenarios on the same method).
- Each test body is split into Arrange / Act / Assert sections.
- `mock_controller` and `mock_router` come from the shared fixtures in
  tests/conftest.py; `view` has no shared fixture, so it is a local
  MagicMock() in every test.
"""
from unittest.mock import MagicMock
from src.gui.features.input.InputScreenPresenter import InputScreenPresenter
from src.application.ImportBoundary import ImportMode, ImportResult
from src.application.viewmodels.ProgramViewModel import ProgramViewModel

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
# TC-ISP-006b: test generate clicked shows a dialog and does not start
# generation when no study program is selected.
# ===========================================================================
def test_presenter_on_generate_clicked_no_programs(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = []
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_generate_clicked()

    # Assert
    assert view.set_program_error.call_args[0] == ("Please select at least one study program.",)
    assert view.show_program_selection_error.call_count == 1
    assert view.show_program_selection_error.call_args[0] == (
        "Please select at least one study program before generating a schedule.",
    )
    assert mock_controller.generate_schedules.call_count == 0
    assert view.set_running_mode.call_count == 0

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
# TC-ISP-007b: test load courses success narrows the available programs to
# those found in the loaded courses, before refreshing the generate button.
# ===========================================================================
def test_presenter_on_load_courses_updates_available_programs(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "courses.csv"
    view.is_replace_mode_selected.return_value = True
    view.selected_program_ids.return_value = ["83108"]

    res = ImportResult(success=True, loaded_count=3, errors=[])
    mock_controller.load_file.return_value = res
    courses = ["course-stub"]
    mock_controller.get_loaded_courses.return_value = courses

    program_vms = [ProgramViewModel(program_id="83108", display_name="Industrial Eng.", course_count=3)]
    mapper = MagicMock()
    mapper.to_program_vms.return_value = program_vms
    mapper.to_program_courses_vm.return_value = []
    mock_controller.get_mapper.return_value = mapper

    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_load_courses_clicked()

    # Assert
    mapper.to_program_vms.assert_called_once_with(courses)
    assert view.set_available_programs.call_count == 1
    assert view.set_available_programs.call_args[0] == (program_vms,)

    # The selector must be refreshed before the generate button validates against it
    method_names = [call[0] for call in view.method_calls]
    assert method_names.index("set_available_programs") < method_names.index("set_generate_button_state")

# ===========================================================================
# TC-ISP-007c: test load courses failure never touches the program selector.
# ===========================================================================
def test_presenter_on_load_courses_failure_skips_available_programs(mock_controller, mock_router):
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
    assert view.set_available_programs.call_count == 0

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

# ===========================================================================
# TC-ISP-012: test load periods (clicked) handles success, mirroring the
# courses-side success test.
# ===========================================================================
def test_presenter_on_load_periods_clicked_success(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "periods.csv"
    view.is_replace_mode_selected.return_value = True

    res = ImportResult(success=True, loaded_count=4, errors=[])
    mock_controller.load_file.return_value = res
    mock_controller.get_loaded_periods.return_value = []
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_load_periods_clicked()

    # Assert
    assert mock_controller.load_file.call_count == 1
    assert mock_controller.load_file.call_args[0] == ("periods.csv", "periods", ImportMode.REPLACE)
    assert presenter._periods_loaded is True
    assert view.mark_periods_loaded.call_count == 1
    assert view.mark_periods_loaded.call_args[0] == (4,)

# ===========================================================================
# TC-ISP-013: test load periods (clicked) handles failure, mirroring the
# courses-side failure test.
# ===========================================================================
def test_presenter_on_load_periods_clicked_failure(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "periods.csv"
    view.is_replace_mode_selected.return_value = False

    res = ImportResult(success=False, loaded_count=0, errors=["Bad date range"])
    mock_controller.load_file.return_value = res
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_load_periods_clicked()

    # Assert
    assert mock_controller.load_file.call_args[0] == ("periods.csv", "periods", ImportMode.UPDATE)
    assert presenter._periods_loaded is False
    assert view.show_import_error.call_count == 1
    assert view.show_import_error.call_args[0] == ("periods", "Bad date range")

# ===========================================================================
# TC-ISP-014: test on_load_periods (direct, mode-supplied) shows the period
# editor when the mapped view models list is non-empty.
# ===========================================================================
def test_presenter_on_load_periods_direct_shows_editor(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.prompt_for_file.return_value = "periods.csv"

    res = ImportResult(success=True, loaded_count=1, errors=[])
    mock_controller.load_file.return_value = res
    periods = ["period-stub"]
    mock_controller.get_loaded_periods.return_value = periods
    mapper = MagicMock()
    period_vms = [MagicMock(name="period_vm")]
    mapper.to_period_edit_vms.return_value = period_vms
    mock_controller.get_mapper.return_value = mapper
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_load_periods(ImportMode.UPDATE)

    # Assert
    assert mock_controller.load_file.call_args[0] == ("periods.csv", "periods", ImportMode.UPDATE)
    assert view.show_period_editor.call_count == 1
    assert view.show_period_editor.call_args[0] == (period_vms,)

# ===========================================================================
# TC-ISP-015: test on_cancel_clicked delegates to the generation collaborator
# — cancels scheduling, resets running mode, and clears progress text.
# ===========================================================================
def test_presenter_on_cancel_clicked_delegates_to_generation(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_cancel_clicked()

    # Assert
    assert mock_controller.cancel_scheduling.call_count == 1
    assert view.set_running_mode.call_count == 1
    assert view.set_running_mode.call_args[0] == (False, "")
    assert view.set_progress_text.call_count == 1
    assert view.set_progress_text.call_args[0] == ("",)

# ===========================================================================
# TC-ISP-016: test on_search_finished delegates to the generation
# collaborator and navigates when schedules were found.
# ===========================================================================
def test_presenter_on_search_finished_delegates_to_generation(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    mock_controller.get_page_info.return_value = {"total_count": 2}
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_search_finished()

    # Assert
    assert view.set_running_mode.call_args[0] == (False, "")
    assert mock_router.show.call_count == 1
    assert mock_router.show.call_args[0] == ("output",)

# ===========================================================================
# TC-ISP-017: test on_error_occurred delegates to the generation
# collaborator, surfacing the scheduler error via the view.
# ===========================================================================
def test_presenter_on_error_occurred_delegates_to_generation(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_error_occurred("Disk is full.")

    # Assert
    assert view.set_running_mode.call_args[0] == (False, "")
    assert view.show_scheduler_error.call_count == 1
    assert view.show_scheduler_error.call_args[0] == ("Disk is full.",)

# ===========================================================================
# TC-ISP-018: test on_view_results_clicked routes directly to the output
# screen, bypassing GenerationPresenter entirely (no generation state is
# touched).
# ===========================================================================
def test_presenter_on_view_results_clicked_routes_directly(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    # Act
    presenter.on_view_results_clicked()

    # Assert
    assert mock_router.show.call_count == 1
    assert mock_router.show.call_args[0] == ("output",)
    assert mock_controller.generate_schedules.call_count == 0
    assert view.set_running_mode.call_count == 0

# ===========================================================================
# TC-ISP-019: test on_settings_clicked delegates to ConstraintsPresenter,
# opening the dialog with the controller's current configuration.
# ===========================================================================
def test_presenter_on_settings_clicked_delegates_to_constraints(mock_controller, mock_router):
    # Arrange
    from unittest.mock import patch

    view = MagicMock()
    current_config = MagicMock(name="current_config")
    mock_controller.get_constraints_config.return_value = current_config
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")

    with patch(
        "gui.features.input.ConstraintsPresenter.ConstraintsSettingsDialog"
    ) as mock_dialog_cls:
        mock_dialog_instance = MagicMock()
        mock_dialog_cls.return_value = mock_dialog_instance

        # Act
        presenter.on_settings_clicked()

        # Assert
        assert mock_controller.get_constraints_config.call_count == 1
        _, kwargs = mock_dialog_cls.call_args
        assert kwargs["current_config"] is current_config
        assert mock_dialog_instance.exec.call_count == 1

# ===========================================================================
# TC-ISP-020: test on_constraints_saved delegates to ConstraintsPresenter,
# pushing the updated period view models then refreshing the generate button.
# ===========================================================================
def test_presenter_on_constraints_saved_delegates_to_constraints(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    updated_vms = [MagicMock(name="period_vm")]

    # Act
    presenter.on_constraints_saved(updated_vms)

    # Assert
    assert mock_controller.update_exam_periods.call_count == 1
    assert mock_controller.update_exam_periods.call_args[0] == (updated_vms,)
    # on_changed == refresh_generate_button, which always re-validates programs.
    assert view.set_generate_button_state.call_count == 1

# ===========================================================================
# TC-ISP-021: test on_enter calls refresh_generate_button so the button's
# state is correct as soon as the screen becomes visible.
# ===========================================================================
def test_presenter_on_enter_calls_refresh_generate_button(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    view.selected_program_ids.return_value = ["83101"]
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    presenter.refresh_generate_button = MagicMock()

    # Act
    presenter.on_enter()

    # Assert
    assert presenter.refresh_generate_button.call_count == 1

# ===========================================================================
# TC-ISP-022: test refresh_generate_button's invalid-dates branch using a
# lightweight fake view with a real is_period_range_valid attribute set to
# False — a bare MagicMock()'s auto-attribute is always truthy and would
# never exercise this branch.
# ===========================================================================
def test_presenter_refresh_generate_button_invalid_dates(mock_controller, mock_router):
    # Arrange
    class FakeView:
        def __init__(self):
            self.is_period_range_valid_value = False
            self.generate_button_calls = []
            self.validation_messages = []
            self.program_errors = []

        def is_period_range_valid(self):
            return self.is_period_range_valid_value

        def selected_program_ids(self):
            return ["83101"]

        def set_generate_button_state(self, enabled, tooltip):
            self.generate_button_calls.append((enabled, tooltip))

        def set_validation_message(self, message):
            self.validation_messages.append(message)

        def set_program_error(self, message):
            self.program_errors.append(message)

    view = FakeView()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    presenter._courses_loaded = True
    presenter._periods_loaded = True

    # Act
    presenter.refresh_generate_button()

    # Assert
    assert view.generate_button_calls == [
        (False, "Fix the exam period dates (end is before start) to continue.")
    ]
    assert view.validation_messages == ["Exam period end date is before the start date."]

# ===========================================================================
# TC-ISP-023: test refresh_generate_button's valid-dates branch using the
# same lightweight fake view, confirming the button is enabled and no
# validation message is shown when dates are valid and files are loaded.
# ===========================================================================
def test_presenter_refresh_generate_button_valid_dates(mock_controller, mock_router):
    # Arrange
    class FakeView:
        def __init__(self):
            self.is_period_range_valid_value = True
            self.generate_button_calls = []
            self.validation_messages = []
            self.program_errors = []

        def is_period_range_valid(self):
            return self.is_period_range_valid_value

        def selected_program_ids(self):
            return ["83101"]

        def set_generate_button_state(self, enabled, tooltip):
            self.generate_button_calls.append((enabled, tooltip))

        def set_validation_message(self, message):
            self.validation_messages.append(message)

        def set_program_error(self, message):
            self.program_errors.append(message)

    view = FakeView()
    presenter = InputScreenPresenter(view, mock_controller, mock_router, "output")
    presenter._courses_loaded = True
    presenter._periods_loaded = True

    # Act
    presenter.refresh_generate_button()

    # Assert
    assert view.generate_button_calls == [(True, "")]
    assert view.validation_messages == [""]
