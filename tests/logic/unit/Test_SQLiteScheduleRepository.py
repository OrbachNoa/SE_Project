"""
Test suite for SQLiteScheduleRepository.

Scope   : Persistence of compressed schedule batches, paging, lazy score updates,
          and dynamic sort indexing.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SSR-001, TC-SSR-002, TC-SSR-003, TC-SSR-004
Fixtures: tmp_path, make_course, make_period
"""
import sqlite3
import zlib
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
from src.application.dto.PackedScheduleCodec import pack_rows
from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA


# A tiny mock Slot to satisfy row_to_dto during unpack
class FakeSlot:
    def __init__(self, course, semester, moed, candidate_dates):
        self.course = course
        self.semester = semester
        self.moed = moed
        self.candidateDates = candidate_dates


# Helper to create a realistic-looking packed blob for 1 slot
def make_packed_blob(num_schedules: int, slot_count: int = 1) -> bytes:
    import struct
    rows = []
    for i in range(num_schedules):
        # Let's say every assignment chose index 0 in the candidateDates list
        rows.append(struct.pack(f"<{slot_count}H", *([0] * slot_count)))
    return zlib.compress(pack_rows(rows, slot_count, num_schedules))


@pytest.fixture
def empty_repo(tmp_path):
    db_file = tmp_path / "test_repo.sqlite"
    repo = SQLiteScheduleRepository(db_path=str(db_file), extra_score_criteria=["ext_1"])
    yield repo
    repo.close()


# TC-SSR-001
def test_insert_and_count_updates_total_count(empty_repo):
    # Arrange
    assert empty_repo.count() == 0
    blob = make_packed_blob(3)

    # Act
    empty_repo.insert_compressed_batch(data=blob, batch_count=3, batch_scores=[{}, {}, {}])

    # Assert
    assert empty_repo.count() == 3
    assert empty_repo.count_scores() == 3


# TC-SSR-002
def test_get_sorted_ids_page_returns_correct_ids_and_uses_indexes(empty_repo):
    # Arrange
    blob = make_packed_blob(3)
    # Give schedule 0 a low score, schedule 1 a high score, schedule 2 a mid score
    crit = ALL_CRITERIA[0]
    scores = [{crit: 10.0}, {crit: 90.0}, {crit: 50.0}]
    empty_repo.insert_compressed_batch(data=blob, batch_count=3, batch_scores=scores)

    # Act
    # Priority sorting by the first criterion (DESC)
    ids_page = empty_repo.get_sorted_ids_page(priority=[crit], offset=0, limit=2)

    # Assert
    # Highest score first: index 1, then index 2
    assert ids_page == [1, 2]
    # Check that the index was created
    with empty_repo._lock:
        indexes = empty_repo._conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        index_names = [r[0] for r in indexes]
        # Should contain an index for this sort order
        assert any("idx_sort" in name for name in index_names)


# TC-SSR-003
def test_update_extended_scores_updates_database(empty_repo):
    # Arrange
    blob = make_packed_blob(1)
    # Insert with empty scores
    empty_repo.insert_compressed_batch(data=blob, batch_count=1, batch_scores=[{}])
    
    # Act
    empty_repo.update_extended_scores(gidxs=[0], score_rows=[{"ext_1": 42.5}])

    # Assert
    # We can read it back via read_score_vectors
    gidxs, vectors = empty_repo.read_score_vectors(criteria=["ext_1"], gidxs=[0])
    assert gidxs == [0]
    assert vectors[0][0] == 42.5


# TC-SSR-004
def test_get_schedules_by_ids_decodes_packed_blob_and_returns_dto(empty_repo, make_course):
    # Arrange
    course = make_course("C101")
    slot = FakeSlot(course, "FALL", "A", [date(2023, 1, 1)])
    empty_repo.configure_slots([slot])

    blob = make_packed_blob(2, slot_count=1)
    empty_repo.insert_compressed_batch(data=blob, batch_count=2, batch_scores=[{"crit_dummy": 1.0}, {"crit_dummy": 2.0}])

    # Act
    dtos = empty_repo.get_schedules_by_ids([1])

    # Assert
    assert len(dtos) == 1
    dto = dtos[0]
    assert isinstance(dto, ScheduleDTO)
    assert len(dto.assignments) == 1
    assert dto.assignments[0].course_id == "C101"
    assert dto.assignments[0].date == "2023-01-01"
