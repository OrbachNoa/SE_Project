"""
Test suite for PackedScheduleCodec.

Scope   : Binary pack/unpack round-trips for compact schedule batch blobs,
          the 16-bit size guards, magic-byte validation, selective row
          unpacking, schedule encoding into slot-aligned date indexes, and
          row-to-DTO reconstruction including its defensive fallback for a
          course with no program entries.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-PSC-001 .. TC-PSC-013
Fixtures: make_course, make_period, make_assignment (tests/conftest.py)
"""
from datetime import date

import pytest

from src.application.dto.PackedScheduleCodec import (
    MAGIC,
    encode_schedule,
    is_packed_blob,
    pack_rows,
    row_to_dto,
    unpack_rows,
    unpack_rows_at,
)
from src.logic.SlotBuilder import Slot
from src.models.Enums import Moed, Semester


def _build_slot(make_course, course_id="10101", dates=None):
    """Helper: build one Slot with a real Course and a small candidate-date list."""
    if dates is None:
        dates = [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]
    course = make_course(course_id=course_id)
    return Slot(course, Semester.FALL, Moed.ALEPH, dates)


# TC-PSC-001
# pack_rows followed by unpack_rows must return the exact slot_count and the
# exact sequence of integer rows that were packed, since every downstream
# consumer (SQLite storage, queue transport) depends on a lossless round trip.
def test_pack_rows_and_unpack_rows_round_trip_multiple_rows():
    # Arrange
    import struct
    rows = [
        struct.pack("<3H", 0, 1, 2),
        struct.pack("<3H", 2, 1, 0),
        struct.pack("<3H", 1, 1, 1),
    ]

    # Act
    blob = pack_rows(rows, slot_count=3, row_count=len(rows))
    slot_count, unpacked = unpack_rows(blob)

    # Assert
    assert slot_count == 3
    assert unpacked == [(0, 1, 2), (2, 1, 0), (1, 1, 1)]


# TC-PSC-002
# The packed format reserves 16 bits for slot_count, so a slot_count above
# 65535 must be rejected up front rather than silently truncated.
def test_pack_rows_raises_value_error_for_slot_count_overflow():
    # Arrange
    rows = [b""]

    # Act / Assert
    with pytest.raises(ValueError):
        pack_rows(rows, slot_count=65536, row_count=1)


# TC-PSC-003
# Symmetric guard for row_count: the header field is also 16 bits wide.
def test_pack_rows_raises_value_error_for_row_count_overflow():
    # Arrange
    rows = [b"\x00\x00"]

    # Act / Assert
    with pytest.raises(ValueError):
        pack_rows(rows, slot_count=1, row_count=65536)


# TC-PSC-004
# is_packed_blob must recognize a real packed blob by its magic prefix.
def test_is_packed_blob_true_for_real_packed_data():
    # Arrange
    blob = pack_rows([b"\x00\x00"], slot_count=1, row_count=1)

    # Act
    result = is_packed_blob(blob)

    # Assert
    assert result is True


# TC-PSC-005
# is_packed_blob must reject arbitrary data (e.g. a legacy pickle blob) that
# does not start with the packed-format magic bytes.
def test_is_packed_blob_false_for_unrelated_bytes():
    # Arrange
    legacy_blob = b"\x80\x04\x95\x00\x00\x00"  # looks like a pickle opcode stream

    # Act
    result = is_packed_blob(legacy_blob)

    # Assert
    assert result is False
    assert not legacy_blob.startswith(MAGIC)


# TC-PSC-006
# unpack_rows must raise ValueError when the magic bytes do not match, so
# callers never silently misinterpret foreign data as a packed batch.
def test_unpack_rows_raises_value_error_on_bad_magic():
    # Arrange
    bad_blob = b"XXXXX" + b"\x01\x00\x01\x00" + b"\x00\x00"

    # Act / Assert
    with pytest.raises(ValueError):
        unpack_rows(bad_blob)


# TC-PSC-007
# unpack_rows_at must return only the requested rows, keyed by their original
# row index, without materializing the rows that were not asked for.
def test_unpack_rows_at_returns_only_requested_rows():
    # Arrange
    import struct
    rows = [
        struct.pack("<2H", 0, 0),
        struct.pack("<2H", 1, 1),
        struct.pack("<2H", 2, 2),
    ]
    blob = pack_rows(rows, slot_count=2, row_count=3)

    # Act
    slot_count, selected = unpack_rows_at(blob, [0, 2])

    # Assert
    assert slot_count == 2
    assert set(selected.keys()) == {0, 2}
    assert selected[0] == (0, 0)
    assert selected[2] == (2, 2)


# TC-PSC-008
# unpack_rows_at must raise IndexError for a row index outside the packed
# batch's row_count, since silently returning nothing would hide a caller bug.
def test_unpack_rows_at_raises_index_error_for_out_of_range_row():
    # Arrange
    import struct
    rows = [struct.pack("<1H", 5)]
    blob = pack_rows(rows, slot_count=1, row_count=1)

    # Act / Assert
    with pytest.raises(IndexError):
        unpack_rows_at(blob, [3])


# TC-PSC-009
# encode_schedule must place each assignment's date index at the slot
# position that matches the slot's (course, semester, moed) identity, and
# leave every other slot at its default zero value.
def test_encode_schedule_produces_correct_row_for_real_schedule(make_course, make_assignment):
    # Arrange
    dates_a = [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]
    dates_b = [date(2026, 6, 10), date(2026, 6, 11)]
    course_a = make_course(course_id="10101")
    course_b = make_course(course_id="10102")
    slot_a = Slot(course_a, Semester.FALL, Moed.ALEPH, dates_a)
    slot_b = Slot(course_b, Semester.FALL, Moed.ALEPH, dates_b)
    slots = [slot_a, slot_b]

    assignment_a = make_assignment(course=course_a, exam_date=dates_a[2], moed=Moed.ALEPH)

    from src.models.Domain import ExamSchedule
    schedule = ExamSchedule()
    schedule.addAssignment(assignment_a)

    assignment_to_slot = {
        (slot.course, slot.semester, slot.moed): i for i, slot in enumerate(slots)
    }
    date_index_by_slot = [{d: i for i, d in enumerate(slot.candidateDates)} for slot in slots]

    # Act
    import struct
    row_bytes = encode_schedule(schedule, assignment_to_slot, date_index_by_slot, len(slots))
    row = struct.unpack("<2H", row_bytes)

    # Assert
    assert row[0] == 2  # dates_a[2] is at index 2
    assert row[1] == 0  # slot_b has no assignment, defaults to index 0


# TC-PSC-010
# row_to_dto must rebuild a ScheduleDTO whose assignments carry the correct
# course identity, resolved date, and program_requirements pairs, matching
# the original Slot/course data the row was encoded against.
def test_row_to_dto_rebuilds_correct_schedule_dto(make_course, make_program_entry):
    # Arrange
    program_entry = make_program_entry(program_id="83101")
    course = make_course(course_id="10101", program_entries=[program_entry])
    dates = [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]
    slot = Slot(course, Semester.FALL, Moed.ALEPH, dates)
    row = (1,)  # date index 1 -> dates[1]

    # Act
    dto = row_to_dto(row, [slot])

    # Assert
    assert dto.total_assignments == 1
    assert len(dto.assignments) == 1
    assignment_dto = dto.assignments[0]
    assert assignment_dto.course_id == "10101"
    assert assignment_dto.date == dates[1].isoformat()
    assert assignment_dto.semester == "FALL"
    assert assignment_dto.moed == "ALEPH"
    assert assignment_dto.program_requirements == [("83101", "OBLIGATORY")]


# TC-PSC-011
# row_to_dto must fall back to an empty program_requirements list when the
# course's programEntries attribute is None, rather than raising, since
# `course.programEntries or []` is meant to guard exactly this case. The
# make_course fixture always substitutes a default entry list when None is
# passed in, so the Course is built directly here to force the real None.
def test_row_to_dto_defaults_program_requirements_when_program_entries_is_none():
    # Arrange
    from src.models.Domain import Course
    from src.models.Enums import EvalType
    course = Course(
        course_id="10101",
        name="Calculus 1",
        instructor="Dr. Cohen",
        evaluation=EvalType.EXAM,
        program_entries=None,
    )
    dates = [date(2026, 6, 1)]
    slot = Slot(course, Semester.FALL, Moed.ALEPH, dates)
    row = (0,)

    # Act
    dto = row_to_dto(row, [slot])

    # Assert
    assert dto.assignments[0].program_requirements == []


# TC-PSC-012
# row_to_dto must attach the scores dict verbatim when one is supplied, so a
# schedule rebuilt from storage keeps its precomputed sort scores.
def test_row_to_dto_attaches_supplied_scores():
    # Arrange — no assignments needed; only the scores propagation is tested.
    row: tuple = ()
    scores = {"MANDATORY_SPAN": 12.5}

    # Act
    dto = row_to_dto(row, [], scores=scores)

    # Assert
    assert dto.scores == {"MANDATORY_SPAN": 12.5}
    assert dto.assignments == []


# TC-PSC-013
# encode_schedule -> pack_rows -> unpack_rows -> row_to_dto must compose into
# a single lossless pipeline end to end, mirroring how QueueScheduleObserver
# and SQLiteScheduleRepository actually use these functions together.
def test_full_pipeline_encode_pack_unpack_row_to_dto_round_trips(make_course, make_assignment):
    # Arrange
    dates = [date(2026, 6, 1), date(2026, 6, 2)]
    course = make_course(course_id="10101")
    slot = Slot(course, Semester.FALL, Moed.ALEPH, dates)
    slots = [slot]
    assignment = make_assignment(course=course, exam_date=dates[1], moed=Moed.ALEPH)

    from src.models.Domain import ExamSchedule
    schedule = ExamSchedule()
    schedule.addAssignment(assignment)

    assignment_to_slot = {(slot.course, slot.semester, slot.moed): 0}
    date_index_by_slot = [{d: i for i, d in enumerate(dates)}]

    # Act
    encoded = encode_schedule(schedule, assignment_to_slot, date_index_by_slot, 1)
    blob = pack_rows([encoded], slot_count=1, row_count=1)
    slot_count, rows = unpack_rows(blob)
    dto = row_to_dto(rows[0], slots)

    # Assert
    assert slot_count == 1
    assert len(rows) == 1
    assert dto.assignments[0].date == dates[1].isoformat()
    assert dto.assignments[0].course_id == "10101"
