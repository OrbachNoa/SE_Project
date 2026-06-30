"""
Test suite for InputImportPresenter.

Scope   : Verifies file import flows, view updates, and error handling.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-IMP-001..004
"""
from unittest.mock import MagicMock
from src.gui.features.input.InputImportPresenter import InputImportPresenter
from src.application.ImportBoundary import ImportMode

class DummyResult:
    def __init__(self, success, errors=None, loaded_count=0):
        self.success = success
        self.errors = errors or []
        self.loaded_count = loaded_count


# TC-GUI-IMP-001
# InputImportPresenter must abort silently if the user cancels the file dialog.
def test_import_presenter_cancels_dialog_silently():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_loaded = MagicMock()
    
    view.prompt_for_file.return_value = ""  # User cancelled dialog
    presenter = InputImportPresenter(view, controller, on_loaded)
    
    # Act
    presenter.on_load_courses(ImportMode.REPLACE)
    presenter.on_load_periods(ImportMode.REPLACE)
    
    # Assert
    assert not presenter.courses_loaded
    assert not presenter.periods_loaded
    controller.load_file.assert_not_called()
    view.show_import_error.assert_not_called()


# TC-GUI-IMP-002
# InputImportPresenter must show an error dialog if the file import fails.
def test_import_presenter_handles_import_failure():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_loaded = MagicMock()
    
    view.prompt_for_file.return_value = "fake_path.csv"
    controller.load_file.return_value = DummyResult(success=False, errors=["Format error"])
    
    presenter = InputImportPresenter(view, controller, on_loaded)
    
    # Act
    presenter.on_load_courses(ImportMode.REPLACE)
    
    # Assert
    assert not presenter.courses_loaded
    view.show_import_error.assert_called_once_with("courses", "Format error")
    view.mark_courses_loaded.assert_not_called()


# TC-GUI-IMP-003
# InputImportPresenter must update the view and trigger on_loaded on successful import.
def test_import_presenter_handles_import_success():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_loaded = MagicMock()
    
    view.prompt_for_file.return_value = "fake_path.csv"
    controller.load_file.return_value = DummyResult(success=True, loaded_count=5)
    controller.get_loaded_courses.return_value = ["course1"]
    
    mapper = MagicMock()
    mapper.to_program_vms.return_value = ["prog_vms"]
    mapper.to_program_courses_vm.return_value = ["course_vms"]
    controller.get_mapper.return_value = mapper
    
    presenter = InputImportPresenter(view, controller, on_loaded)

    # Act
    presenter.on_load_courses(ImportMode.REPLACE)

    # Assert
    assert presenter.courses_loaded is True
    view.mark_courses_loaded.assert_called_once_with(5)
    view.set_available_programs.assert_called_once_with(["prog_vms"])
    view.render_courses.assert_called_once_with(["course_vms"])
    on_loaded.assert_called_once()


# TC-GUI-IMP-004
# InputImportPresenter must forward the chosen UPDATE mode to the controller
# unchanged (rather than always importing in REPLACE mode), so an "update"
# import merges into the existing data instead of overwriting it.
def test_import_presenter_forwards_update_mode():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    on_loaded = MagicMock()

    view.prompt_for_file.return_value = "fake_path.csv"
    controller.load_file.return_value = DummyResult(success=True, loaded_count=3)
    controller.get_loaded_courses.return_value = ["course1"]

    mapper = MagicMock()
    mapper.to_program_vms.return_value = ["prog_vms"]
    mapper.to_program_courses_vm.return_value = ["course_vms"]
    controller.get_mapper.return_value = mapper

    presenter = InputImportPresenter(view, controller, on_loaded)

    # Act
    presenter.on_load_courses(ImportMode.UPDATE)

    # Assert — the selected UPDATE mode reaches load_file verbatim, and the
    # successful import still updates the loaded state and notifies the caller.
    controller.load_file.assert_called_once_with("fake_path.csv", "courses", ImportMode.UPDATE)
    assert presenter.courses_loaded is True
    view.mark_courses_loaded.assert_called_once_with(3)
    on_loaded.assert_called_once()
