"""
Test suite for CubeCollectorObserver.

Scope   : Verifies on_schedule_found() builds one WorkUnit per call with the
          correct seed_dates extracted from the schedule's assignments, that
          collected units accumulate across multiple calls, and that the
          remaining IScheduleObserver methods (on_progress, should_cancel,
          on_finished, on_error) are pure no-ops that never raise.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CCO-001, TC-CCO-002, ...
Fixtures: make_assignment, empty_schedule (shared)
"""
from datetime import date

from src.logic.observers.CubeCollectorObserver import CubeCollectorObserver
from src.logic.parallel.WorkUnit import WorkUnit


# ---------------------------------------------------------------------------
# on_schedule_found TC-CCO-001..004
# ---------------------------------------------------------------------------

# TC-CCO-001
# on_schedule_found must append exactly one WorkUnit whose seed_dates tuple
# matches the dates of the schedule's assignments, in assignment order.
def test_on_schedule_found_builds_work_unit_from_assignment_dates(
    make_course, make_assignment, empty_schedule,
):
    # Arrange
    observer = CubeCollectorObserver()
    schedule = empty_schedule
    course_a = make_course(course_id="A")
    course_b = make_course(course_id="B")
    schedule.addAssignment(make_assignment(course=course_a, exam_date=date(2026, 6, 1)))
    schedule.addAssignment(make_assignment(course=course_b, exam_date=date(2026, 6, 5)))

    # Act
    observer.on_schedule_found(schedule)

    # Assert
    assert len(observer.units) == 1
    assert observer.units[0] == WorkUnit(seed_dates=(date(2026, 6, 1), date(2026, 6, 5)))


# TC-CCO-002
# on_schedule_found called on an empty schedule must produce a WorkUnit with
# an empty seed_dates tuple, not raise or skip the unit.
def test_on_schedule_found_with_empty_schedule_produces_empty_seed_dates(empty_schedule):
    # Arrange
    observer = CubeCollectorObserver()

    # Act
    observer.on_schedule_found(empty_schedule)

    # Assert
    assert observer.units == [WorkUnit(seed_dates=())]


# TC-CCO-003
# Multiple calls to on_schedule_found must accumulate one WorkUnit per call,
# preserving call order in the units list.
def test_on_schedule_found_accumulates_one_unit_per_call(
    make_course, make_assignment, empty_schedule,
):
    # Arrange
    observer = CubeCollectorObserver()
    first_schedule = empty_schedule
    first_schedule.addAssignment(make_assignment(course=make_course(course_id="A"), exam_date=date(2026, 6, 1)))

    second_schedule_course = make_course(course_id="B")
    second_schedule = empty_schedule.__class__()
    second_schedule.addAssignment(make_assignment(course=second_schedule_course, exam_date=date(2026, 6, 9)))

    # Act
    observer.on_schedule_found(first_schedule)
    observer.on_schedule_found(second_schedule)

    # Assert
    assert len(observer.units) == 2
    assert observer.units[0].seed_dates == (date(2026, 6, 1),)
    assert observer.units[1].seed_dates == (date(2026, 6, 9),)


# TC-CCO-004
# The units property must expose the same list instance the observer has
# been accumulating into, so callers reading it after partitioning see every
# unit collected so far.
def test_units_property_reflects_all_collected_units(
    make_course, make_assignment, empty_schedule,
):
    # Arrange
    observer = CubeCollectorObserver()
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=make_course(course_id="A"), exam_date=date(2026, 6, 3)))

    # Act
    observer.on_schedule_found(schedule)
    units_before = len(observer.units)
    observer.on_schedule_found(schedule)
    units_after = len(observer.units)

    # Assert
    assert units_before == 1
    assert units_after == 2


# ---------------------------------------------------------------------------
# No-op lifecycle methods TC-CCO-005..006
# ---------------------------------------------------------------------------

# TC-CCO-005
# on_progress, should_cancel, on_finished and on_error must all be callable
# without raising, and should_cancel must always report False since this
# collector never controls cancellation.
def test_lifecycle_noop_methods_do_not_raise_and_should_cancel_is_false():
    # Arrange
    observer = CubeCollectorObserver()

    # Act
    observer.on_progress(50)
    cancel_result = observer.should_cancel()
    observer.on_finished()
    observer.on_error("some error")

    # Assert
    assert cancel_result is False


# TC-CCO-006
# on_error must not affect the collected units list -- errors are handled by
# the caller, not stored on the collector.
def test_on_error_does_not_modify_collected_units(
    make_course, make_assignment, empty_schedule,
):
    # Arrange
    observer = CubeCollectorObserver()
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(course=make_course(course_id="A"), exam_date=date(2026, 6, 1)))
    observer.on_schedule_found(schedule)

    # Act
    observer.on_error("partition failed")

    # Assert
    assert len(observer.units) == 1
