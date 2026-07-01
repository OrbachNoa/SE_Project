"""Unit tests for OutputScreenPresenter — the output screen's coordination layer.

The presenter mediates between the view (mocked here) and the controller:
it formats the solution counter and page-bar labels from raw state, drives
calendar rendering from a ScheduleViewModel, guards PDF/TXT export against
an empty result set or an exam-less schedule, recovers cleanly when reading
or exporting a schedule fails (routing every failure through
controller.map_error rather than a raw exception string), and stops the
background sort worker on screen exit.

Conventions:
- Each test carries a unique TC-OSP-NNN identifier in the comment block
  above its definition, numbered sequentially (with a lettered variant,
  015b, for a closely related scenario on the same method).
- Each test body is split into Arrange / Act / Assert sections.
- `controller` and `router` come from the shared `mock_controller` /
  `mock_router` fixtures in tests/conftest.py; `view` has no shared
  fixture, so it is a local MagicMock() in every test.
"""
from unittest.mock import MagicMock
from src.gui.features.output.OutputScreenPresenter import OutputScreenPresenter
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel, ScheduleItemViewModel
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-OSP-001: with zero solutions, the counter must read "No solutions" and
# every navigation/export control must be disabled — there is nothing to
# navigate to or export.
# ===========================================================================
def test_presenter_refresh_counter_zero_solutions(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 0

    # Act
    presenter.refresh_counter()

    # Assert
    assert view.set_solution_counter.call_count == 1
    assert view.set_solution_counter.call_args[0] == ("No solutions",)
    assert view.set_solution_controls.call_count == 1
    assert view.set_solution_controls.call_args.kwargs == {"can_prev": False, "can_next": False, "can_export": False}

# ===========================================================================
# TC-OSP-002: with several solutions and a mid-range current index, the
# counter must show the 1-based position out of the total, and every
# navigation/export control must be enabled.
# ===========================================================================
def test_presenter_refresh_counter_multiple_solutions(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 5
    presenter._current_index = 2

    # Act
    presenter.refresh_counter()

    # Assert
    assert view.set_solution_counter.call_count == 1
    assert view.set_solution_counter.call_args[0] == ("Solution 3 / 5",)
    assert view.set_solution_controls.call_count == 1
    assert view.set_solution_controls.call_args.kwargs == {"can_prev": True, "can_next": True, "can_export": True}

# ===========================================================================
# TC-OSP-003: with only a single page of results, the database paging bar
# must be hidden entirely — paging controls are meaningless with one page.
# ===========================================================================
def test_presenter_refresh_page_bar_single_page(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 1

    # Act
    presenter.refresh_page_bar()

    # Assert
    assert view.set_page_bar_visible.call_count == 1
    assert view.set_page_bar_visible.call_args[0] == (False,)

# ===========================================================================
# TC-OSP-004: on page 1 of 3 with the next page already materialised in
# SQLite (sqlite_count above the window threshold), next/last must be
# enabled and first/previous must be disabled.
# ===========================================================================
def test_presenter_refresh_page_bar_multiple_pages_next_ready(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0
    presenter._sqlite_count = 15_000

    # Act
    presenter.refresh_page_bar()

    # Assert
    assert view.set_page_bar.call_count == 1
    assert view.set_page_bar.call_args.kwargs == {
        "visible": True,
        "label": "Page 1 / 3",
        "can_first": False,
        "can_previous": False,
        "can_next": True,
        "can_last": True
    }

# ===========================================================================
# TC-OSP-005: the same page-1-of-3 setup, but with sqlite_count below the
# window threshold — next/last must now be disabled, since the next page's
# rows have not been persisted to SQLite yet.
# ===========================================================================
def test_presenter_refresh_page_bar_multiple_pages_next_not_ready(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0
    presenter._sqlite_count = 5_000  # < 10,000

    # Act
    presenter.refresh_page_bar()

    # Assert
    assert view.set_page_bar.call_count == 1
    assert view.set_page_bar.call_args.kwargs == {
        "visible": True,
        "label": "Page 1 / 3",
        "can_first": False,
        "can_previous": False,
        "can_next": False,
        "can_last": False
    }

# ===========================================================================
# TC-OSP-006: on_next_page() must ask the controller to load the next page
# and refresh the presenter's own page/total state from what the
# controller reports back — not assume the requested page succeeded as-is.
# ===========================================================================
def test_presenter_page_loads(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router
    controller.get_page_info.return_value = {
        "current_page": 1,
        "total_pages": 3,
        "total_count": 30,
        "window_size": 10,
        "sqlite_count": 25_000
    }

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total_pages = 3
    presenter._current_page = 0

    # Act
    presenter.on_next_page()

    # Assert
    assert controller.load_page.call_count == 1
    assert controller.load_page.call_args[0] == (1,)
    assert presenter._current_page == 1
    assert presenter._total == 10

# ===========================================================================
# TC-OSP-007: show_current() must filter the schedule's excluded dates and
# items down to the period currently being viewed, and paint only the
# matching items onto the calendar grid for that date range.
# ===========================================================================
def test_presenter_show_current_renders_calendar(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    p1 = PeriodEditViewModel(semester="FALL", moed="ALEPH", start_date="2026-06-01", end_date="2026-06-05", excluded_dates=["2026-06-02"])
    item1 = ScheduleItemViewModel(date="2026-06-03", title="Course A", subtitle="83100", tooltip="Details")
    item2 = ScheduleItemViewModel(date="2026-06-10", title="Course B", subtitle="83200", tooltip="Details")

    schedule_view = ScheduleViewModel(items=[item1, item2], current_index=0, total=1)
    controller.get_schedule_view.return_value = schedule_view

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1
    presenter._periods.reset([p1])

    # Act
    presenter.show_current()

    # Assert
    assert view.set_screen_updates.call_count == 2
    assert view.set_screen_updates.call_args_list[0][0] == (False,)
    assert view.set_screen_updates.call_args_list[1][0] == (True,)

    assert view.set_period_navigation.call_count == 1
    assert view.set_period_navigation.call_args[0] == ("Semester FALL - Moed ALEPH (1/1)", False, False)

    assert view.render_calendar.call_count == 1
    args = view.render_calendar.call_args[0]
    assert args[0] == ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
    assert args[1] == ["2026-06-02"]
    assert len(args[2]) == 1
    assert args[2][0].date == "2026-06-03"

# ===========================================================================
# TC-OSP-008: test show_current handles errors when reading schedule fails.
# ===========================================================================
def test_presenter_show_current_handles_exception(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    error = Exception("Database read failure")
    controller.get_schedule_view.side_effect = error
    controller.map_error.return_value = "Could not read the schedule. Please try again."

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.show_current()

    # Assert — the presenter delegates mapping to the controller (no raw
    # f"{error}" formatting) and shows whatever message map_error returns.
    assert controller.map_error.call_count == 1
    assert controller.map_error.call_args[0][0] is error
    assert controller.map_error.call_args[0][1]["operation"] == "render_calendar"
    assert view.show_display_error.call_count == 1
    assert "Could not read the schedule. Please try again." in view.show_display_error.call_args[0][0]
    assert view.set_screen_updates.call_count == 2
    assert view.set_screen_updates.call_args_list[0][0] == (False,)
    assert view.set_screen_updates.call_args_list[1][0] == (True,)

# ===========================================================================
# TC-OSP-009: test export pdf is rejected when total is 0.
# ===========================================================================
def test_presenter_export_pdf_guard_total_zero(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 0

    # Act
    presenter.on_export_pdf()

    # Assert
    assert view.show_nothing_to_export.call_count == 1
    assert view.show_nothing_to_export.call_args[0] == ("There is no schedule to export yet.",)

# ===========================================================================
# TC-OSP-010: test export pdf is rejected when schedule has no exams.
# ===========================================================================
def test_presenter_export_pdf_guard_empty_schedule(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    empty_view = ScheduleViewModel(items=[], current_index=0, total=1)
    controller.get_schedule_view.return_value = empty_view

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.on_export_pdf()

    # Assert
    assert view.show_nothing_to_export.call_count == 1
    assert view.show_nothing_to_export.call_args[0] == ("This schedule has no exams to export.",)

# ===========================================================================
# TC-OSP-011: test export pdf handles errors when reading schedule fails.
# ===========================================================================
def test_presenter_export_pdf_handles_exception(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    error = Exception("Export retrieval failure")
    controller.get_schedule_view.side_effect = error
    controller.map_error.return_value = "Could not read the schedule. Please try again."

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.on_export_pdf()

    # Assert
    assert controller.map_error.call_count == 1
    assert controller.map_error.call_args[0][0] is error
    assert controller.map_error.call_args[0][1]["export_format"] == "pdf"
    assert view.show_export_error.call_count == 1
    assert "Could not read the schedule. Please try again." in view.show_export_error.call_args[0][0]

# ===========================================================================
# TC-OSP-012: test export pdf executes successfully on valid schedule.
# ===========================================================================
def test_presenter_export_pdf_success(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    valid_view = ScheduleViewModel(items=[ScheduleItemViewModel(date="2026-06-01", title="A", subtitle="B", tooltip="C")], current_index=0, total=1)
    controller.get_schedule_view.return_value = valid_view

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.on_export_pdf()

    # Assert
    assert view.export_schedule_pdf.call_count == 1
    assert view.export_schedule_pdf.call_args[0] == (valid_view, 0)

# ===========================================================================
# TC-OSP-013: test on_leave disables active state without blocking on worker completion.
# ===========================================================================
def test_presenter_on_leave_retires_running_worker_without_waiting(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._is_active = True

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    presenter._sort_worker = mock_worker

    # Act
    presenter.on_leave()

    # Assert
    assert presenter._is_active is False
    assert mock_worker.quit.call_count == 1
    assert mock_worker.wait.call_count == 0
    assert mock_worker in presenter._retired_sort_workers
    assert presenter._sort_worker is None

# ===========================================================================
# TC-OSP-014: test on_export_txt delegates to controller correctly.
# ===========================================================================
def test_presenter_on_export_txt_success(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    valid_view = ScheduleViewModel(items=[ScheduleItemViewModel(date="2026-06-01", title="A", subtitle="B", tooltip="C")], current_index=0, total=1)
    controller.get_schedule_view.return_value = valid_view
    view.ask_save_path.return_value = "C:/test/path.txt"

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.on_export_txt()

    # Assert
    assert view.ask_save_path.call_count == 1
    assert controller.save_schedule.call_count == 1
    assert controller.save_schedule.call_args[0] == (0, "C:/test/path.txt")
    assert view.show_message.call_count == 1

# ===========================================================================
# TC-OSP-015: test on_export_txt rejected when total is zero.
# ===========================================================================
def test_presenter_on_export_txt_guard_total_zero(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 0

    # Act
    presenter.on_export_txt()

    # Assert
    assert view.show_nothing_to_export.call_count == 1
    assert controller.save_schedule.call_count == 0


# ===========================================================================
# TC-OSP-015b: on_export_txt save failure shows the mapped message as-is —
# no "Could not save schedule:" prefix restating what the message already
# says (the dialog title "Export error" already gives that context).
# ===========================================================================
def test_presenter_on_export_txt_save_failure_shows_message_without_prefix(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router

    valid_view = ScheduleViewModel(
        items=[ScheduleItemViewModel(date="2026-06-01", title="A", subtitle="B", tooltip="C")],
        current_index=0,
        total=1,
    )
    controller.get_schedule_view.return_value = valid_view
    view.ask_save_path.return_value = "C:/test/path.txt"
    controller.save_schedule.side_effect = PermissionError("denied")
    controller.map_error.return_value = "The file could not be written. Please close it and try again."

    presenter = OutputScreenPresenter(view, controller, router)
    presenter._total = 1

    # Act
    presenter.on_export_txt()

    # Assert
    assert view.show_export_error.call_args[0][0] == (
        "The file could not be written. Please close it and try again."
    )


# ===========================================================================
# TC-OSP-016: a SortWorker failure's structured AppErrorInfo (last_error)
# reaches the controller's technical log, not just the GUI message.
# ===========================================================================
def test_presenter_on_sort_failed_logs_structured_error_via_controller(mock_controller, mock_router):
    # Arrange
    from src.application.errors.ErrorModel import AppErrorInfo, ErrorCategory, ErrorSeverity

    view = MagicMock()
    controller = mock_controller
    router = mock_router

    presenter = OutputScreenPresenter(view, controller, router)
    info = AppErrorInfo(
        code="PERSISTENCE_IO_FAILED",
        category=ErrorCategory.PERSISTENCE,
        severity=ErrorSeverity.ERROR,
        user_message="Could not sort. Please try again.",
        technical_message="OSError during sort",
        recoverable=True,
    )
    mock_worker = MagicMock()
    mock_worker.last_error = info
    presenter._sort_worker = mock_worker

    # Act — the worker's `failed` signal already carries only the user message.
    presenter._on_sort_failed("Could not sort. Please try again.")

    # Assert — the structured record reaches the controller's technical log,
    # in addition to the message shown via view.show_error.
    assert controller.log_worker_error.call_count == 1
    assert controller.log_worker_error.call_args[0][0] is info
    assert view.show_error.call_count == 1


# ===========================================================================
# TC-OSP-017: map_export_error delegates to controller.map_error with the
# PDF export operation/path context — this is what SchedulePdfExporter calls
# when the HTML/Qt-printing step fails outside any presenter try/except.
# ===========================================================================
def test_presenter_map_export_error_delegates_to_controller(mock_controller, mock_router):
    # Arrange
    view = MagicMock()
    controller = mock_controller
    router = mock_router
    controller.map_error.return_value = "The file could not be written. Please try again."

    presenter = OutputScreenPresenter(view, controller, router)
    error = PermissionError("denied")

    # Act
    message = presenter.map_export_error(error, "out.pdf")

    # Assert
    assert message == "The file could not be written. Please try again."
    assert controller.map_error.call_count == 1
    call_error, context = controller.map_error.call_args[0]
    assert call_error is error
    assert context["operation"] == "export_pdf"
    assert context["screen"] == "output"
    assert context["path"] == "out.pdf"
