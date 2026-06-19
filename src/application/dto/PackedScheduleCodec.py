from __future__ import annotations

import struct
from typing import Iterable, List, Sequence

from src.application.dto.ScheduleDTO import AssignmentDTO, ScheduleDTO

MAGIC = b"ESPK1"
_HEADER = struct.Struct("<5sHH")
_UINT16 = struct.Struct("<H")


def pack_rows(rows: Iterable[bytes], slot_count: int, row_count: int) -> bytes:
    """Pack already encoded schedule rows into one compact batch blob."""
    return _HEADER.pack(MAGIC, slot_count, row_count) + b"".join(rows)


def is_packed_blob(data: bytes) -> bool:
    return data.startswith(MAGIC)


def unpack_rows(data: bytes) -> tuple[int, List[tuple[int, ...]]]:
    """Return (slot_count, rows) from a compact batch blob."""
    magic, slot_count, row_count = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError("not a packed schedule blob")

    row_size = slot_count * _UINT16.size
    offset = _HEADER.size
    rows = []
    for _ in range(row_count):
        row_data = data[offset:offset + row_size]
        rows.append(struct.unpack(f"<{slot_count}H", row_data))
        offset += row_size
    return slot_count, rows


def encode_schedule(schedule, assignment_to_slot: dict, date_index_by_slot: Sequence[dict], slot_count: int) -> bytes:
    """Encode one complete schedule as date indexes aligned to the slots list."""
    values = [0] * slot_count
    for assignment in schedule.assignments:
        slot_index = assignment_to_slot[(assignment.course, assignment.semester, assignment.moed)]
        values[slot_index] = date_index_by_slot[slot_index][assignment.date]
    return struct.pack(f"<{slot_count}H", *values)


def row_to_dto(row: Sequence[int], slots: Sequence, scores: dict | None = None) -> ScheduleDTO:
    """Materialize one packed row back into the GUI-facing DTO shape."""
    assignments = []
    for slot, date_index in zip(slots, row):
        assignment_date = slot.candidateDates[date_index]
        course = slot.course
        assignments.append(
            AssignmentDTO(
                course_id=course.courseId,
                course_name=course.name,
                instructor=course.instructor,
                evaluation=course.evaluation.value if hasattr(course.evaluation, "value") else str(course.evaluation),
                date=assignment_date.isoformat(),
                semester=slot.semester.value if hasattr(slot.semester, "value") else slot.semester,
                moed=slot.moed.value if hasattr(slot.moed, "value") else slot.moed,
                program_requirements=[
                    (
                        entry.programId,
                        entry.requirement.value if hasattr(entry.requirement, "value") else str(entry.requirement),
                    )
                    for entry in (course.programEntries or [])
                ],
            )
        )
    return ScheduleDTO(
        assignments=assignments,
        total_assignments=len(assignments),
        scores=scores or {},
    )
