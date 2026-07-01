"""
Automated end-to-end (E2E) integration tests for the GUI experience.

These tests use pytest-qt (qtbot) to simulate user actions headlessly (offscreen).
The test pipeline covers:
- Loading course and period files (in both replace and update modes).
- Mocking file dialogs, program selectors, and user actions on cards.
- Simulating schedule generation and waiting for early output routing.
- Navigating the generated solutions and exporting output schedules to PDF.

Conventions:
- Each test carries a unique TC-GUI-E2E-NNN identifier in the comment
  block above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- `MockIntegrationController` and `StubWorker` (below) are local QObject
  subclasses with real PyQt signals, used instead of the shared
  `mock_controller` fixture — a plain MagicMock's `.emit()` never invokes
  connected slots, so these E2E flows need genuine signal/slot wiring to
  exercise the real screens end-to-end. `viewmodel_mapper` comes from the
  shared fixture in tests/conftest.py; `make_schedule_dto` likewise.
"""

from datetime import date
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QStackedWidget
from src.gui.core.ScreenRouter import ScreenRouter
from src.gui.features.input.InputScreen import InputScreen
from src.gui.features.output.OutputScreen import OutputScreen
from src.application.ImportBoundary import ImportResult, ImportMode
from src.models.Domain import ExamPeriod, Course, ProgramEntry
from src.models.Enums import Semester, Moed, Requirement, EvalType
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# -------------------------------------------
# Helpers
# -------------------------------------------

# -- Mock class for controller  --
class MockIntegrationController(QObject):
    """AppController stub with real PyQt6 signals for integration tests."""
    schedule_found = pyqtSignal(object)
    progress_updated = pyqtSignal(int)
    search_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    early_results_ready = pyqtSignal()
    total_count_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.load_file = MagicMock()
        self.get_loaded_courses = MagicMock()
        self.get_loaded_periods = MagicMock()
        self.generate_schedules = MagicMock()
        self.get_mapper = MagicMock()
        self.get_page_info = MagicMock(return_value={
            "current_page": 0,
            "total_pages": 1,
            "total_count": 0,
            "window_size": 0,
            "sqlite_count": 0,
        })
        self.get_schedule_view = MagicMock()
        self.update_exam_periods = MagicMock()

# -- Stub worker to simulate background QThread worker signals in tests --
class StubWorker(QObject):
    """QObject stub worker to simulate background QThread worker signals in tests."""
    schedules_batch_found = pyqtSignal(int)
    schedule_found = pyqtSignal(object)
    search_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def start(self) -> None:
        pass

    def isRunning(self) -> bool:
        return False


# Builds minimal Course objects so the program selector card has real choices
# to offer — InputScreenPresenter.on_load_courses_clicked only calls
# set_available_programs when get_loaded_courses returns a non-empty list, and
# the card's mousePressEvent only opens the dialog when it has program choices.
def _make_courses_for_programs(program_ids):
    return [
        Course(
            course_id=f"900{index:02d}",
            name=f"Course for program {program_id}",
            instructor="Staff",
            evaluation=EvalType.EXAM,
            program_entries=[
                ProgramEntry(program_id=program_id, year=1, semester=Semester.FALL, requirement=Requirement.OBLIGATORY)
            ],
        )
        for index, program_id in enumerate(program_ids)
    ]


# ===========================================================================
# TC-GUI-E2E-001: test E2E flow of loading data and generating a schedule.
# ===========================================================================
def test_schedule_generation_flow(qtbot, viewmodel_mapper):
    """
    Conceptual prototype showing how to wire the E2E simulation using qtbot.
    Run this with QT_QPA_PLATFORM=offscreen for headless execution.
    """
    # Arrange
    # container that holds all screens; only one is visible at a time
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    # Set up mock controller
    controller = MockIntegrationController()
    # Set up viewmodel mapper
    controller.get_mapper.return_value = viewmodel_mapper
    # Configure periods returned when output screen is initialized
    p = ExamPeriod(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        excluded_dates=[]
    )
    # Configure loaded periods
    controller.get_loaded_periods.return_value = [p]
    # Configure page info and schedule views for the solution bar
    controller.get_page_info.return_value = {
        "current_page": 0,
        "total_pages": 1,
        "total_count": 2,
        "window_size": 2,
        "sqlite_count": 2,
    }
    # Configure schedule views
    view0 = ScheduleViewModel(items=[], current_index=0, total=2)
    view1 = ScheduleViewModel(items=[], current_index=1, total=2)
    controller.get_schedule_view.side_effect = [view0, view1, view0]
    # Set up input and output screens
    input_screen = InputScreen(controller, router)
    output_screen = OutputScreen(controller, router)
    # Register screens with router
    router.register("input", input_screen)
    router.register("output", output_screen)
    router.show("input")
    # Register widgets with the bot
    qtbot.addWidget(stack)
    # Mock native File and Message boxes to avoid thread blocking
    courses_path = "tests/fixtures/sample_courses.csv"
    periods_path = "tests/fixtures/sample_periods.csv"
    pdf_path = "tests/fixtures/exported_schedule.pdf"
    # Directly mock the file prompt method on the input screen to return paths
    input_screen.prompt_for_file = MagicMock(side_effect=[courses_path, periods_path])
    # Mock file dialog and message boxes
    with patch("gui.features.output.widgets.SchedulePdfExporter.QFileDialog.getSaveFileName") as mock_save, \
         patch("src.gui.features.input.InputScreen.QMessageBox.information"), \
         patch("src.gui.features.input.InputScreen.QMessageBox.critical"):
        # Mock save file dialog
        mock_save.return_value = (pdf_path, "PDF Files (*.pdf)")
        # Configure mock responses from controller/facade
        controller.load_file.side_effect = [
            ImportResult(success=True, loaded_count=10, errors=[]),
            ImportResult(success=True, loaded_count=2, errors=[])
        ]
        # Configure mock responses from controller/facade — non-empty so the
        # program selector card actually has choices to offer once courses load.
        controller.get_loaded_courses.return_value = _make_courses_for_programs(["83101", "83102"])
        # Act & Assert
        # Import Actions - Simulate loading courses
        qtbot.mouseClick(input_screen.action_bar.courses_load_btn, Qt.MouseButton.LeftButton)
        assert controller.load_file.call_count == 1
        # Simulate loading periods
        qtbot.mouseClick(input_screen.action_bar.periods_load_btn, Qt.MouseButton.LeftButton)
        assert controller.load_file.call_count == 2
        # Program Selection Action — the card opens a real ProgramSelectorDialog
        # internally, so the dialog class itself is patched (same pattern as
        # Test_ProgramSelectorCardWidget.py) instead of stubbing a selection helper.
        with patch(
            "gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
        ) as mock_dialog_cls:
            mock_dialog_cls.return_value.exec.return_value = True
            mock_dialog_cls.return_value.selected_ids.return_value = ["83101", "83102"]
            # Click on card to open selector popup
            qtbot.mouseClick(input_screen.program_selector_card, Qt.MouseButton.LeftButton)
        assert input_screen.selected_program_ids() == ["83101", "83102"]
        # Run Generation - Simulate scheduler run trigger
        qtbot.mouseClick(input_screen.action_bar.generate_btn, Qt.MouseButton.LeftButton)
        assert controller.generate_schedules.call_count == 1
        assert controller.generate_schedules.call_args[0] == (["83101", "83102"],)
        # Simulate early results signal arrival
        controller.early_results_ready.emit()
        # Assert router successfully transitioned to the Output Screen
        assert router._current_name() == "output"
        # Verify Output screen navigations — clicking next must actually
        # advance to the second schedule (view1, current_index=1) before
        # clicking back returns to the input screen; the old version never
        # checked next_btn's effect at all, only the final router state
        # after back_btn.
        qtbot.mouseClick(output_screen.solution_bar.next_btn, Qt.MouseButton.LeftButton)
        assert output_screen.solution_bar.solution_input.text() == "2"
        qtbot.mouseClick(output_screen.solution_bar.back_btn, Qt.MouseButton.LeftButton)
        # Navigate back to input
        assert router._current_name() == "input"


# ===========================================================================
# TC-GUI-E2E-002: test E2E flow exporting schedule as a PDF file.
# ===========================================================================
def test_export_pdf_flow(qtbot, viewmodel_mapper):
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    controller = MockIntegrationController()
    controller.get_mapper.return_value = viewmodel_mapper

    p = ExamPeriod(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        excluded_dates=[]
    )
    controller.get_loaded_periods.return_value = [p]

    controller.get_page_info.return_value = {
        "current_page": 0,
        "total_pages": 1,
        "total_count": 1,
        "window_size": 1,
        "sqlite_count": 1,
    }

    item = ScheduleItemViewModel(
        date="2026-06-05",
        title="Software Engineering",
        subtitle="83-311",
        tooltip="Details"
    )
    view = ScheduleViewModel(items=[item], current_index=0, total=1)
    controller.get_schedule_view.return_value = view

    input_screen = InputScreen(controller, router)
    output_screen = OutputScreen(controller, router)

    router.register("input", input_screen)
    router.register("output", output_screen)
    router.show("input")

    qtbot.addWidget(stack)

    courses_path = "tests/fixtures/sample_courses.csv"
    periods_path = "tests/fixtures/sample_periods.csv"

    input_screen.prompt_for_file = MagicMock(side_effect=[courses_path, periods_path])
    output_screen.export_schedule_pdf = MagicMock()

    with patch("src.gui.features.input.InputScreen.QMessageBox.information"):
        controller.load_file.side_effect = [
            ImportResult(success=True, loaded_count=10, errors=[]),
            ImportResult(success=True, loaded_count=2, errors=[])
        ]
        # Non-empty so the program selector card actually has choices to
        # offer once courses load — matching test_schedule_generation_flow
        # and test_update_import_and_generate. With an empty list here, the
        # card never reaches the (patched) dialog below at all: it shows its
        # own "No courses loaded" guard and returns early, so no program is
        # ever selected and the later generate click hits a real, unpatched
        # "Program selection required" warning instead of exporting anything.
        controller.get_loaded_courses.return_value = _make_courses_for_programs(["83100"])

        # Load courses
        qtbot.mouseClick(input_screen.action_bar.courses_load_btn, Qt.MouseButton.LeftButton)
        # Load periods
        qtbot.mouseClick(input_screen.action_bar.periods_load_btn, Qt.MouseButton.LeftButton)

        # Select programs — the card opens a real ProgramSelectorDialog
        # internally, so the dialog class itself is patched (same pattern as
        # Test_ProgramSelectorCardWidget.py) instead of stubbing a selection helper.
        with patch(
            "gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
        ) as mock_dialog_cls:
            mock_dialog_cls.return_value.exec.return_value = True
            mock_dialog_cls.return_value.selected_ids.return_value = ["83100"]
            qtbot.mouseClick(input_screen.program_selector_card, Qt.MouseButton.LeftButton)

        # The dialog path was genuinely exercised, not just "didn't crash".
        assert input_screen.selected_program_ids() == ["83100"]

        # Click generate
        qtbot.mouseClick(input_screen.action_bar.generate_btn, Qt.MouseButton.LeftButton)
        controller.early_results_ready.emit()

        # Now on output screen
        assert router._current_name() == "output"

        # Act
        output_screen.solution_bar.export_btn.menu().actions()[0].trigger()

        # Assert
        assert output_screen.export_schedule_pdf.call_count == 1
        assert output_screen.export_schedule_pdf.call_args[0][1] == 0


# ===========================================================================
# TC-GUI-E2E-003: test E2E flow performing update imports and schedule generation.
# ===========================================================================
def test_update_import_and_generate(qtbot, viewmodel_mapper):
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    controller = MockIntegrationController()
    controller.get_mapper.return_value = viewmodel_mapper

    input_screen = InputScreen(controller, router)
    output_screen = OutputScreen(controller, router)

    router.register("input", input_screen)
    router.register("output", output_screen)
    router.show("input")

    qtbot.addWidget(stack)
    stack.show()
    qtbot.waitExposed(stack)

    courses_path = "tests/fixtures/sample_courses.csv"
    periods_path = "tests/fixtures/sample_periods.csv"

    input_screen.prompt_for_file = MagicMock(side_effect=[courses_path, periods_path])

    with patch("src.gui.features.input.InputScreen.QMessageBox.information"):
        controller.load_file.side_effect = [
            ImportResult(success=True, loaded_count=5, errors=[]),
            ImportResult(success=True, loaded_count=1, errors=[])
        ]
        # Non-empty so the program selector card actually has choices to offer
        # once courses load.
        controller.get_loaded_courses.return_value = _make_courses_for_programs(["83100"])

        # Act
        # Toggle mode to UPDATE
        qtbot.mouseClick(input_screen.action_bar.mode_update, Qt.MouseButton.LeftButton)
        assert input_screen.action_bar.mode_update.isChecked() is True

        # Load courses (in update mode)
        qtbot.mouseClick(input_screen.action_bar.courses_load_btn, Qt.MouseButton.LeftButton)
        # Load periods (in update mode)
        qtbot.mouseClick(input_screen.action_bar.periods_load_btn, Qt.MouseButton.LeftButton)

        # Select programs — the card opens a real ProgramSelectorDialog
        # internally, so the dialog class itself is patched (same pattern as
        # Test_ProgramSelectorCardWidget.py) instead of stubbing a selection helper.
        with patch(
            "gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
        ) as mock_dialog_cls:
            mock_dialog_cls.return_value.exec.return_value = True
            mock_dialog_cls.return_value.selected_ids.return_value = ["83100"]
            qtbot.mouseClick(input_screen.program_selector_card, Qt.MouseButton.LeftButton)

        # Click generate
        qtbot.mouseClick(input_screen.action_bar.generate_btn, Qt.MouseButton.LeftButton)

        # Assert
        assert controller.load_file.call_count == 2
        assert controller.load_file.call_args_list[0][0] == (courses_path, "courses", ImportMode.UPDATE)
        assert controller.load_file.call_args_list[1][0] == (periods_path, "periods", ImportMode.UPDATE)

        assert controller.generate_schedules.call_count == 1
        assert controller.generate_schedules.call_args[0] == (["83100"],)


# ===========================================================================
# TC-GUI-E2E-004: test E2E flow exporting schedule to a PDF file that actually writes to disk.
# ===========================================================================
def test_export_pdf_actual_file(qtbot, viewmodel_mapper, tmp_path):
    # Arrange
    stack = QStackedWidget()
    router = ScreenRouter(stack)
    controller = MockIntegrationController()
    controller.get_mapper.return_value = viewmodel_mapper

    p = ExamPeriod(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        excluded_dates=[]
    )
    controller.get_loaded_periods.return_value = [p]

    controller.get_page_info.return_value = {
        "current_page": 0,
        "total_pages": 1,
        "total_count": 1,
        "window_size": 1,
        "sqlite_count": 1,
    }

    item = ScheduleItemViewModel(
        date="2026-06-05",
        title="Software Engineering",
        subtitle="83-311\nID: 83311",
        tooltip="Software Engineering\nFall · Aleph"
    )
    view = ScheduleViewModel(items=[item], current_index=0, total=1)
    controller.get_schedule_view.return_value = view

    input_screen = InputScreen(controller, router)
    output_screen = OutputScreen(controller, router)

    router.register("input", input_screen)
    router.register("output", output_screen)
    router.show("input")

    qtbot.addWidget(stack)

    courses_path = "tests/fixtures/sample_courses.csv"
    periods_path = "tests/fixtures/sample_periods.csv"
    pdf_path = str(tmp_path / "actual_test_export.pdf")

    input_screen.prompt_for_file = MagicMock(side_effect=[courses_path, periods_path])

    # Patch QFileDialog and QMessageBox to avoid thread blocking
    with patch("gui.features.output.widgets.SchedulePdfExporter.QFileDialog") as mock_file_dialog, \
         patch("gui.features.output.widgets.SchedulePdfExporter.QMessageBox") as mock_message_box:

        mock_file_dialog.getSaveFileName.return_value = (pdf_path, "PDF Files (*.pdf)")

        controller.load_file.side_effect = [
            ImportResult(success=True, loaded_count=10, errors=[]),
            ImportResult(success=True, loaded_count=2, errors=[])
        ]
        # Non-empty so the program selector card actually has choices to
        # offer once courses load — matching test_schedule_generation_flow
        # and test_update_import_and_generate. With an empty list here, the
        # card never reaches the (patched) dialog below at all: it shows its
        # own "No courses loaded" guard and returns early, so no program is
        # ever selected and the later generate click hits a real, unpatched
        # "Program selection required" warning instead of exporting anything.
        controller.get_loaded_courses.return_value = _make_courses_for_programs(["83100"])

        # Load courses
        qtbot.mouseClick(input_screen.action_bar.courses_load_btn, Qt.MouseButton.LeftButton)
        # Load periods
        qtbot.mouseClick(input_screen.action_bar.periods_load_btn, Qt.MouseButton.LeftButton)

        # Select programs — the card opens a real ProgramSelectorDialog
        # internally, so the dialog class itself is patched (same pattern as
        # Test_ProgramSelectorCardWidget.py) instead of stubbing a selection helper.
        with patch(
            "gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
        ) as mock_dialog_cls:
            mock_dialog_cls.return_value.exec.return_value = True
            mock_dialog_cls.return_value.selected_ids.return_value = ["83100"]
            qtbot.mouseClick(input_screen.program_selector_card, Qt.MouseButton.LeftButton)

        # The dialog path was genuinely exercised, not just "didn't crash".
        assert input_screen.selected_program_ids() == ["83100"]

        # Click generate
        qtbot.mouseClick(input_screen.action_bar.generate_btn, Qt.MouseButton.LeftButton)
        controller.early_results_ready.emit()

        # Now on output screen
        assert router._current_name() == "output"

        # Act
        output_screen.solution_bar.export_btn.menu().actions()[0].trigger()

        # Assert
        assert mock_file_dialog.getSaveFileName.call_count == 1
        assert mock_message_box.information.call_count == 1
        assert mock_message_box.critical.call_count == 0

        # Verify that the file actually exists and has content
        import os
        assert os.path.exists(pdf_path) is True
        assert os.path.getsize(pdf_path) > 0

        # Clean up the file
        try:
            os.remove(pdf_path)
        except OSError:
            pass


# ===========================================================================
# TC-GUI-E2E-005: test E2E flow with real components performing update loads and generating schedules.
# ===========================================================================
def test_update_import_and_real_pipeline(qtbot, tmp_path):
    # Imports locally to avoid module caching issues
    import zlib
    from src.application.dto.PackedScheduleCodec import pack_rows
    from src.application.services.FileImportService import FileImportService
    from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
    from src.application.state.HybridScheduleResultState import HybridScheduleResultState
    from src.application.state.InputDataState import InputDataState
    from src.infrastructure.cache.DiskCacheRepository import DiskCacheRepository
    from src.infrastructure.cache.FileChangeDetector import FileChangeDetector
    from src.application.services.InputCacheService import InputCacheService
    from src.file_io.parsers.ParserFactory import ParserFactory
    from src.application.services.InputDataMerger import InputDataMerger
    from src.application.services.SchedulingService import SchedulingService
    from src.application.services.ScheduleExportService import ScheduleExportService
    from src.file_io.writers.TextFileWriter import TextFileWriter
    from src.application.services.ViewModelMapper import ViewModelMapper
    from src.application.AppController import AppController

    # Arrange & Set up real components using tmp_path for db isolation
    db_path = str(tmp_path / "test_real_pipeline.sqlite")
    schedule_repository = SQLiteScheduleRepository(db_path=db_path)
    hybrid_state = HybridScheduleResultState(repository=schedule_repository)
    input_state = InputDataState()

    # Use tmp_path for the disk cache so each test run is fully isolated
    # (shared .cache/data_cache.pkl leaks data across runs in UPDATE mode)
    cache_repository = DiskCacheRepository(cache_path=tmp_path / "data_cache.pkl")
    cache_detector = FileChangeDetector()

    importer = FileImportService(
        cache_service=InputCacheService(cache_repository, cache_detector),
        parser_factory=ParserFactory(),
        merger=InputDataMerger(input_state),
        state=input_state,
    )

    scheduler = SchedulingService(repository=schedule_repository)
    exporter = ScheduleExportService(writer=TextFileWriter())
    mapper = ViewModelMapper()

    controller = AppController(
        importer=importer,
        scheduler=scheduler,
        exporter=exporter,
        mapper=mapper,
        input_state=input_state,
        schedule_state=hybrid_state,
    )

    stack = QStackedWidget()
    router = ScreenRouter(stack)

    input_screen = InputScreen(controller, router)
    output_screen = OutputScreen(controller, router)

    router.register("input", input_screen)
    router.register("output", output_screen)
    router.show("input")

    qtbot.addWidget(stack)

    courses_path = "tests/fixtures/courses_valid.txt"
    periods_path = "tests/fixtures/periods_valid.txt"

    input_screen.prompt_for_file = MagicMock(side_effect=[courses_path, periods_path])

    # We mock input QMessageBox to prevent UI popup blocking
    with patch("src.gui.features.input.InputScreen.QMessageBox"), \
         patch("src.application.services.SchedulingService.SchedulingService.generate_async") as mock_generate_async:

        stub_worker = StubWorker()
        mock_generate_async.return_value = stub_worker

        # Act 1: Toggle mode to UPDATE
        qtbot.mouseClick(input_screen.action_bar.mode_update, Qt.MouseButton.LeftButton)

        # Act 2: Load courses and periods
        qtbot.mouseClick(input_screen.action_bar.courses_load_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(input_screen.action_bar.periods_load_btn, Qt.MouseButton.LeftButton)

        # Assert files were loaded into state and widgets populated
        loaded_courses = controller.get_loaded_courses()
        loaded_periods = controller.get_loaded_periods()
        assert len(loaded_courses) > 0
        assert len(loaded_periods) == 2
        assert len(input_screen._course_list_widget._blocks) > 0

        # Act 3: Choose program ID "83101" via card click — the card opens a
        # real ProgramSelectorDialog internally, so the dialog class itself is
        # patched (same pattern as Test_ProgramSelectorCardWidget.py) instead
        # of stubbing a selection helper.
        with patch(
            "gui.features.input.widgets.ProgramSelectorCardWidget.ProgramSelectorDialog"
        ) as mock_dialog_cls:
            mock_dialog_cls.return_value.exec.return_value = True
            mock_dialog_cls.return_value.selected_ids.return_value = ["83101"]
            qtbot.mouseClick(input_screen.program_selector_card, Qt.MouseButton.LeftButton)

        assert input_screen.selected_program_ids() == ["83101"]

        # Act 4: Click generate
        qtbot.mouseClick(input_screen.action_bar.generate_btn, Qt.MouseButton.LeftButton)

        # Assert generate_async called with correct parameters
        assert mock_generate_async.call_count == 1
        call_args = mock_generate_async.call_args[0]
        assert call_args[0] == ["83101"]  # selected program
        # courses and periods match what was actually loaded from fixtures
        assert len(call_args[1]) == len(loaded_courses)
        assert len(call_args[2]) == len(loaded_periods)

        # Insert a packed batch to simulate SQLite output database state.
        # insert_batch no longer exists; the repository's current public API
        # stores packed rows, so configure_slots([]) plus one zero-slot row
        # is the equivalent of "one decodable, empty-assignment schedule
        # exists" -- enough to make count() > 0 and trigger early navigation.
        schedule_repository.configure_slots([])
        packed = pack_rows([b""], slot_count=0, row_count=1)
        schedule_repository.insert_compressed_batch(zlib.compress(packed), 1)

        # Act 5: Simulate generation batch found to trigger router navigation
        stub_worker.schedules_batch_found.emit(1)

        # Assert router successfully transitioned to the Output Screen
        assert router._current_name() == "output"

        # Teardown — finish the simulated run so the controller stops its
        # progress QTimer. generate_schedules() starts a 500 ms polling timer
        # (AppController._start_progress_timer) that is only stopped on the
        # search_finished / cancel paths. Without this emit the timer outlives
        # the test: qtbot deletes this screen's QLabel at teardown, then a later
        # 500 ms poll fires progress_updated into that deleted QLabel and raises
        # "RuntimeError: wrapped C/C++ object of type QLabel has been deleted"
        # during whatever test happens to be running at that moment.
        stub_worker.search_finished.emit()
