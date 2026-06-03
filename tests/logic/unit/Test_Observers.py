import pytest
from unittest.mock import MagicMock
from datetime import date
from src.concurrency.QueueScheduleObserver import QueueScheduleObserver
from src.logic.CollectingScheduleObserver import CollectingScheduleObserver
from src.logic.StreamingScheduleObserver import StreamingScheduleObserver
from src.models.domain import ExamSchedule


# ===========================================================================
# TC-OBS-001: CollectingScheduleObserver collects snapshots of schedules.
# ===========================================================================
def test_collecting_schedule_observer_collects_snapshots(make_assignment):
    # Arrange
    observer = CollectingScheduleObserver()
    schedule = ExamSchedule()
    assignment = make_assignment(exam_date=date(2026, 6, 1))
    schedule.addAssignment(assignment)
    
    # Act
    observer.on_schedule_found(schedule)
    collected = observer.schedules[0]
    schedule.removeAssignment() # Mutate original schedule
    
    # Assert
    assert observer.should_cancel() is False
    assert len(observer.schedules) == 1
    assert len(schedule.assignments) == 0
    assert len(collected.assignments) == 1
    assert collected.assignments[0].course.courseId == "10101"


# ===========================================================================
# TC-OBS-002: QueueScheduleObserver buffers and flushes schedules based on batch_size.
# ===========================================================================
def test_queue_schedule_observer_buffering_and_flush(make_assignment):
    # Arrange
    mock_queue = MagicMock()
    mock_cancel_event = MagicMock()
    observer = QueueScheduleObserver(mock_queue, mock_cancel_event, batch_size=2)
    
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    # Act
    observer.on_schedule_found(schedule)
    call_count_after_first = mock_queue.put.call_count
    
    observer.on_schedule_found(schedule)
    call_count_after_second = mock_queue.put.call_count
    msg_type, payload = mock_queue.put.call_args[0][0]
    
    # Assert
    assert call_count_after_first == 0
    assert call_count_after_second == 1
    assert msg_type == "SCHEDULE_BATCH"
    assert len(payload) == 2
    assert payload[0].assignments[0].course_id == "10101"


# ===========================================================================
# TC-OBS-003: QueueScheduleObserver lifecycle (on_finished, on_error, should_cancel).
# ===========================================================================
def test_queue_schedule_observer_lifecycle(make_assignment):
    # Arrange
    mock_queue = MagicMock()
    mock_cancel_event = MagicMock()
    observer = QueueScheduleObserver(mock_queue, mock_cancel_event, batch_size=5)
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    # Act
    observer.on_progress(75)
    progress_call = mock_queue.put.call_args[0][0]
    
    mock_cancel_event.is_set.return_value = True
    cancelled = observer.should_cancel()
    cancel_event_call_count = mock_cancel_event.is_set.call_count
    
    observer.on_error("Fatal Error")
    error_call = mock_queue.put.call_args[0][0]
    
    observer.on_schedule_found(schedule)
    mock_queue.put.reset_mock()
    
    observer.on_finished()
    finished_call_count = mock_queue.put.call_count
    calls = [call[0][0] for call in mock_queue.put.call_args_list]
    
    # Assert
    assert progress_call == ("PROGRESS", 75)
    assert cancelled is True
    assert cancel_event_call_count == 1
    assert error_call == ("ERROR", "Fatal Error")
    assert finished_call_count == 2
    assert calls[0][0] == "SCHEDULE_BATCH"
    assert len(calls[0][1]) == 1
    assert calls[1] == ("FINISHED", None)


# ===========================================================================
# TC-OBS-004: QueueScheduleObserver handles a null cancel event gracefully.
# ===========================================================================
def test_queue_schedule_observer_with_null_cancel_event():
    # Arrange
    mock_queue = MagicMock()
    observer = QueueScheduleObserver(mock_queue, cancel_event=None, batch_size=5)
    
    # Act
    cancelled = observer.should_cancel()
    
    # Assert
    assert cancelled is False


# ===========================================================================
# TC-OBS-005: StreamingScheduleObserver writes schedules directly to disk and handles lifecycle.
# ===========================================================================
def test_streaming_schedule_observer_lifecycle(tmp_path, make_assignment):
    # Arrange
    output_file = tmp_path / "output.txt"
    observer = StreamingScheduleObserver(str(output_file))
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    empty_output = tmp_path / "empty_output.txt"
    empty_observer = StreamingScheduleObserver(str(empty_output))
    
    error_output = tmp_path / "error_output.txt"
    error_observer = StreamingScheduleObserver(str(error_output))
    
    # Act
    # 1. Test normal streaming write
    observer.on_schedule_found(schedule)
    count_after_found = observer.count
    observer.on_finished()
    normal_output_exists = output_file.exists()
    normal_content = output_file.read_text(encoding="utf-8") if normal_output_exists else ""
    
    # 2. Test empty results case
    empty_observer.on_finished()
    empty_output_exists = empty_output.exists()
    empty_content = empty_output.read_text(encoding="utf-8") if empty_output_exists else ""
    
    # 3. Test error handling case
    error_observer.on_error("Disk Full")
    recorded_error = error_observer.error
    
    # Assert
    assert observer.should_cancel() is False
    assert count_after_found == 1
    assert observer.error is None
    assert normal_output_exists is True
    assert "=== Exam System Option 1 ===" in normal_content
    assert "Calculus 1" in normal_content
    
    assert empty_output_exists is True
    assert empty_content == "No valid exam schedules were generated.\n"
    
    assert recorded_error == "Disk Full"


# ===========================================================================
# TC-OBS-006: StreamingScheduleObserver raises OSError for unwritable output paths.
# ===========================================================================
def test_streaming_schedule_observer_unwritable_path(tmp_path, make_assignment):
    # Arrange - Set output_path to a directory, making writing fail
    invalid_path = tmp_path / "invalid_dir"
    invalid_path.mkdir()
    
    observer = StreamingScheduleObserver(str(invalid_path))
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    # Act & Assert (writing a schedule fails)
    with pytest.raises(OSError):
        observer.on_schedule_found(schedule)
        
    # Act & Assert (writing default empty footer fails)
    empty_observer = StreamingScheduleObserver(str(invalid_path))
    with pytest.raises(OSError):
        empty_observer.on_finished()
