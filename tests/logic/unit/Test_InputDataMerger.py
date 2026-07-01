"""
Test suite for InputDataMerger.

Scope   : REPLACE mode delegating straight to state.replace_courses/
          replace_periods, UPDATE mode merging courses (dedup by courseId,
          incoming wins) and periods (dedup by (semester, moed), incoming
          wins), and an unsupported mode raising ValueError. A real
          InputDataState is used (not a mock) so the merge logic genuinely
          runs end to end against production state methods.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-IDM-001 .. TC-IDM-007
Fixtures: make_course, make_period (tests/conftest.py)
"""
import pytest

from src.application.ImportBoundary import ImportMode
from src.application.services.InputDataMerger import InputDataMerger
from src.application.state.InputDataState import InputDataState


# TC-IDM-001
# REPLACE mode for courses must call state.replace_courses with exactly the
# incoming data, discarding whatever courses were previously loaded.
def test_merge_replace_mode_replaces_courses(make_course):
    # Arrange
    state = InputDataState()
    old_course = make_course(course_id="10101")
    state.replace_courses([old_course])
    merger = InputDataMerger(state)
    new_course = make_course(course_id="20202", name="Algebra")

    # Act
    merger.merge([new_course], ImportMode.REPLACE, "courses")

    # Assert
    result = state.get_courses()
    assert result == [new_course]
    assert old_course not in result


# TC-IDM-002
# REPLACE mode for periods must call state.replace_periods with exactly the
# incoming data, discarding whatever periods were previously loaded.
def test_merge_replace_mode_replaces_periods(make_period):
    # Arrange
    state = InputDataState()
    old_period = make_period()
    state.replace_periods([old_period])
    merger = InputDataMerger(state)
    from src.models.Enums import Semester, Moed
    from datetime import date
    new_period = make_period(semester=Semester.SPRI, moed=Moed.BET,
                              start=date(2026, 7, 1), end=date(2026, 7, 30))

    # Act
    merger.merge([new_period], ImportMode.REPLACE, "periods")

    # Assert
    result = state.get_periods()
    assert result == [new_period]
    assert old_period not in result


# TC-IDM-003
# UPDATE mode for courses must keep existing courses not present in the
# incoming list, and overwrite any course whose courseId matches an
# incoming entry with the incoming version (incoming wins).
def test_merge_update_mode_merges_courses_incoming_wins_on_id_collision(make_course):
    # Arrange
    state = InputDataState()
    existing_a = make_course(course_id="10101", name="Calculus 1")
    existing_b = make_course(course_id="10102", name="Physics 1")
    state.replace_courses([existing_a, existing_b])
    merger = InputDataMerger(state)
    updated_a = make_course(course_id="10101", name="Calculus 1 (Updated)")

    # Act
    merger.merge([updated_a], ImportMode.UPDATE, "courses")

    # Assert
    result = {c.courseId: c for c in state.get_courses()}
    assert set(result.keys()) == {"10101", "10102"}
    assert result["10101"].name == "Calculus 1 (Updated)"
    assert result["10102"] is existing_b


# TC-IDM-004
# UPDATE mode for courses must add a brand-new courseId without removing
# any of the pre-existing courses.
def test_merge_update_mode_adds_new_course_without_removing_others(make_course):
    # Arrange
    state = InputDataState()
    existing = make_course(course_id="10101")
    state.replace_courses([existing])
    merger = InputDataMerger(state)
    brand_new = make_course(course_id="30303", name="Statistics")

    # Act
    merger.merge([brand_new], ImportMode.UPDATE, "courses")

    # Assert
    result_ids = {c.courseId for c in state.get_courses()}
    assert result_ids == {"10101", "30303"}


# TC-IDM-005
# UPDATE mode for periods must dedup by (semester, moed), keeping any
# existing period whose key is absent from the incoming list and
# overwriting any period whose key matches an incoming entry.
def test_merge_update_mode_merges_periods_incoming_wins_on_key_collision(make_period):
    # Arrange
    from datetime import date
    from src.models.Enums import Semester, Moed

    state = InputDataState()
    existing_fall_aleph = make_period(semester=Semester.FALL, moed=Moed.ALEPH,
                                       start=date(2026, 6, 1), end=date(2026, 6, 10))
    existing_fall_bet = make_period(semester=Semester.FALL, moed=Moed.BET,
                                     start=date(2026, 7, 1), end=date(2026, 7, 10))
    state.replace_periods([existing_fall_aleph, existing_fall_bet])
    merger = InputDataMerger(state)
    updated_fall_aleph = make_period(semester=Semester.FALL, moed=Moed.ALEPH,
                                      start=date(2026, 6, 5), end=date(2026, 6, 20))

    # Act
    merger.merge([updated_fall_aleph], ImportMode.UPDATE, "periods")

    # Assert
    result = {(p.semester, p.moed): p for p in state.get_periods()}
    assert set(result.keys()) == {(Semester.FALL, Moed.ALEPH), (Semester.FALL, Moed.BET)}
    assert result[(Semester.FALL, Moed.ALEPH)].startDate == date(2026, 6, 5)
    assert result[(Semester.FALL, Moed.BET)] is existing_fall_bet


# TC-IDM-006
# An unsupported ImportMode value (neither REPLACE nor UPDATE) must raise a
# ValueError rather than silently doing nothing.
def test_merge_raises_value_error_for_unsupported_mode(make_course):
    # Arrange
    state = InputDataState()
    merger = InputDataMerger(state)

    class _BogusMode:
        """Stand-in for an ImportMode value the merger does not recognise."""
        pass

    # Act / Assert
    with pytest.raises(ValueError):
        merger.merge([make_course()], _BogusMode(), "courses")


# TC-IDM-007
# A non-"periods" file_type (e.g. "courses") must route through the course
# merge path even in UPDATE mode, confirming file_type strictly controls
# which state field is touched rather than introspecting the data.
def test_merge_update_mode_treats_unrecognized_file_type_as_courses(make_course):
    # Arrange
    state = InputDataState()
    existing = make_course(course_id="10101")
    state.replace_courses([existing])
    merger = InputDataMerger(state)
    incoming = make_course(course_id="10101", name="Renamed")

    # Act
    merger.merge([incoming], ImportMode.UPDATE, "courses")

    # Assert
    assert state.get_courses() == [incoming]
    assert state.get_periods() == []
