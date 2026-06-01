import pytest
from unittest.mock import MagicMock
from datetime import date
from src.logic.Scheduler import ListScheduleObserver
from src.concurrency.QueueScheduleObserver import QueueScheduleObserver
from src.models.domain import ExamSchedule


def test_list_schedule_observer_collects_clones(make_assignment):
    """Verify that ListScheduleObserver collects and clones found schedules."""
    # Arrange
    observer = ListScheduleObserver()
    assert observer.should_cancel() is False
    
    schedule = ExamSchedule()
    assignment = make_assignment(exam_date=date(2026, 6, 1))
    schedule.addAssignment(assignment)
    
    # Act
    observer.on_schedule_found(schedule)
    
    # Assert
    assert len(observer.schedules) == 1
    collected = observer.schedules[0]
    assert collected is not schedule # Must be a clone
    assert len(collected.assignments) == 1
    assert collected.assignments[0].course.courseId == "10101"
    
    # Act (Mutate original schedule)
    schedule.removeAssignment()
    
    # Assert (Collected schedule should remain unchanged)
    assert len(schedule.assignments) == 0
    assert len(collected.assignments) == 1


def test_queue_schedule_observer_buffering_and_flush(make_assignment):
    """Verify that QueueScheduleObserver buffers and flushes schedules based on batch_size."""
    # Arrange
    mock_queue = MagicMock()
    mock_cancel_event = MagicMock()
    observer = QueueScheduleObserver(mock_queue, mock_cancel_event, batch_size=2)
    
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    # Act (Add first schedule - buffers, no queue put)
    observer.on_schedule_found(schedule)
    
    # Assert
    assert mock_queue.put.call_count == 0
    
    # Act (Add second schedule - exceeds batch_size, should flush)
    observer.on_schedule_found(schedule)
    
    # Assert
    assert mock_queue.put.call_count == 1
    msg_type, payload = mock_queue.put.call_args[0][0]
    assert msg_type == "SCHEDULE_BATCH"
    assert len(payload) == 2
    assert payload[0].assignments[0].course_id == "10101"


def test_queue_schedule_observer_lifecycle(make_assignment):
    """Verify on_finished, on_error, and should_cancel functionality of QueueScheduleObserver."""
    # Arrange
    mock_queue = MagicMock()
    mock_cancel_event = MagicMock()
    observer = QueueScheduleObserver(mock_queue, mock_cancel_event, batch_size=5)
    
    # Act (Test on_progress)
    observer.on_progress(75)
    
    # Assert
    assert mock_queue.put.call_args[0][0] == ("PROGRESS", 75)
    
    # Act & Assert (Test should_cancel)
    mock_cancel_event.is_set.return_value = True
    assert observer.should_cancel() is True
    assert mock_cancel_event.is_set.call_count == 1
    
    # Act (Test on_error)
    observer.on_error("Fatal Error")
    
    # Assert
    assert mock_queue.put.call_args[0][0] == ("ERROR", "Fatal Error")
    
    # Arrange (Test on_finished flushes remaining items)
    schedule = ExamSchedule()
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 1)))
    
    observer.on_schedule_found(schedule) # buffered (1 item)
    mock_queue.put.reset_mock()
    
    # Act
    observer.on_finished()
    
    # Assert (Expect 2 puts: remaining batch, and FINISHED)
    assert mock_queue.put.call_count == 2
    calls = [call[0][0] for call in mock_queue.put.call_args_list]
    assert calls[0][0] == "SCHEDULE_BATCH"
    assert len(calls[0][1]) == 1
    assert calls[1] == ("FINISHED", None)
