"""
Test suite for QueueWorkSource.

Scope   : get_next()'s cancel-event short circuit, its retry loop across
          one or more queue.Empty timeouts before a real item arrives, and
          its None-sentinel stop signal.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-QWS-001 .. TC-QWS-004
Fixtures: none

Hang-prevention note: every mocked queue's get() side_effect list used here
is finite and always ends with either a real returned item or None — never
an unbounded sequence of queue.Empty, since get_next()'s retry loop would
otherwise spin forever on a mock that never stops raising.
"""
import queue as queue_mod
from unittest.mock import MagicMock

from src.infrastructure.concurrency.QueueWorkSource import QueueWorkSource
from src.logic.parallel.WorkUnit import WorkUnit


# TC-QWS-001
# When the cancel event is already set, get_next() must return None
# immediately without ever touching the queue, so a cancelled worker does
# not block waiting on work that will never be consumed.
def test_get_next_returns_none_immediately_when_cancelled():
    # Arrange
    mock_queue = MagicMock()
    cancel_event = MagicMock()
    cancel_event.is_set.return_value = True
    source = QueueWorkSource(mock_queue, cancel_event=cancel_event, poll_timeout=0.01)

    # Act
    result = source.get_next()

    # Assert
    assert result is None
    mock_queue.get.assert_not_called()


# TC-QWS-002
# get_next() must retry through transient queue.Empty timeouts (the queue is
# briefly empty while other work is still being produced) and return the
# first real WorkUnit once it becomes available, without raising.
def test_get_next_retries_through_empty_timeouts_then_returns_item():
    # Arrange
    work_unit = WorkUnit(seed_dates=())
    mock_queue = MagicMock()
    mock_queue.get.side_effect = [queue_mod.Empty(), queue_mod.Empty(), work_unit]
    cancel_event = MagicMock()
    cancel_event.is_set.return_value = False
    source = QueueWorkSource(mock_queue, cancel_event=cancel_event, poll_timeout=0.01)

    # Act
    result = source.get_next()

    # Assert
    assert result is work_unit
    assert mock_queue.get.call_count == 3


# TC-QWS-003
# Pulling the None sentinel from the queue must make get_next() return None,
# signalling this worker to stop — distinct from the queue.Empty retry path.
def test_get_next_returns_none_for_stop_sentinel():
    # Arrange
    mock_queue = MagicMock()
    mock_queue.get.side_effect = [None]
    cancel_event = MagicMock()
    cancel_event.is_set.return_value = False
    source = QueueWorkSource(mock_queue, cancel_event=cancel_event, poll_timeout=0.01)

    # Act
    result = source.get_next()

    # Assert
    assert result is None
    assert mock_queue.get.call_count == 1


# TC-QWS-004
# With no cancel_event supplied at all (None), get_next() must not treat
# that as "always cancelled" — it should still retrieve real items normally.
def test_get_next_works_without_a_cancel_event():
    # Arrange
    work_unit = WorkUnit(seed_dates=())
    mock_queue = MagicMock()
    mock_queue.get.side_effect = [work_unit]
    source = QueueWorkSource(mock_queue, cancel_event=None, poll_timeout=0.01)

    # Act
    result = source.get_next()

    # Assert
    assert result is work_unit
