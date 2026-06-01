import pickle
import pytest
from src.application.dto_viewmodel.schedule_dto import AssignmentDTO, ScheduleDTO
from src.application.dto_viewmodel.ScheduleDTOAdapter import ScheduleDTOAdapter

# -------------------------------------------------------------------------
# TC-DTO-001..007 : Test DTOs boundary between processes
# -------------------------------------------------------------------------


# ===========================================================================
# TC-DTO-001: Test that AssignmentDTO stores fields correctly.
# ===========================================================================
def test_assignment_dto_fields():
    # Arrange & Act
    dto = AssignmentDTO(
        course_id="10101",
        course_name="Calculus 1",
        instructor="Dr. Cohen",
        date="2026-06-01",
        semester="FALL",
        moed="ALEPH"
    )
    # Assert
    assert dto.course_id == "10101"
    assert dto.course_name == "Calculus 1"
    assert dto.instructor == "Dr. Cohen"
    assert dto.date == "2026-06-01"
    assert dto.semester == "FALL"
    assert dto.moed == "ALEPH"


# ===========================================================================
# TC-DTO-002: Test that ScheduleDTO stores assignments and total_assignments correctly.
# ===========================================================================
def test_schedule_dto_fields():
    # Arrange
    a1 = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    a2 = AssignmentDTO("10102", "Algebra", "Dr. Levy", "2026-06-03", "FALL", "ALEPH")
    
    # Act
    dto = ScheduleDTO(assignments=[a1, a2], total_assignments=2)
    
    # Assert
    assert len(dto.assignments) == 2
    assert dto.assignments[0] == a1
    assert dto.assignments[1] == a2
    assert dto.total_assignments == 2


# ===========================================================================
# TC-DTO-003: Test that DTOs can cross the process boundary safely via pickling.
# ===========================================================================
def test_dto_pickle_serialization():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    
    # Act
    serialized = pickle.dumps(schedule)
    deserialized = pickle.loads(serialized)
    
    # Assert
    assert deserialized.total_assignments == 1
    assert len(deserialized.assignments) == 1
    assert deserialized.assignments[0].course_id == "10101"
    assert deserialized.assignments[0].course_name == "Calc 1"


# ===========================================================================
# TC-DTO-004: Test that AssignmentDTO rejects extra attributes due to slots.
# ===========================================================================
def test_assignment_dto_rejects_extra_attributes():
    # Arrange
    dto = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    
    # Act & Assert
    with pytest.raises(AttributeError):
        dto.non_existent_field = "test"  # type: ignore


# ===========================================================================
# TC-DTO-005: Test that AssignmentDTO rejects instantiation with missing arguments.
# ===========================================================================
def test_assignment_dto_missing_arguments():
    # Arrange, Act & Assert
    # missing required positional arguments
    with pytest.raises(TypeError):
        AssignmentDTO(course_id="10101")


# ===========================================================================
# TC-DTO-006: Test that ScheduleDTO rejects extra attributes due to slots.
# ===========================================================================
def test_schedule_dto_rejects_extra_attributes():
    # Arrange
    dto = ScheduleDTO()
    
    # Act & Assert
    with pytest.raises(AttributeError):
        dto.non_existent_field = "test"  


# ===========================================================================
# TC-DTO-007: Test that pickle raises UnpicklingError or EOFError for corrupted serialization.
# ===========================================================================
def test_dto_pickle_deserialization_failure():
    # Arrange
    invalid_data = b"invalid pickled bytes data stream"
    
    # Act & Assert
    with pytest.raises((pickle.UnpicklingError, EOFError, AttributeError, ValueError, TypeError)):
        pickle.loads(invalid_data)


# -------------------------------------------------------------------------
# TC-DTO-008..015 : Test ScheduleDTOAdapter boundary between processes
# -------------------------------------------------------------------------

# ===========================================================================
# TC-DTO-008: Test that ScheduleDTOAdapter correctly adapts valid ScheduleDTO.
# ===========================================================================
def test_schedule_dto_adapter_success():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    
    # Act
    adapter = ScheduleDTOAdapter(schedule)
    
    # Assert
    assert len(adapter.assignments) == 1
    adapted = adapter.assignments[0]
    assert adapted.date.year == 2026
    assert adapted.date.month == 6
    assert adapted.date.day == 1
    assert adapted.semester.name == "FALL"
    assert adapted.moed.name == "ALEPH"
    assert adapted.course.name == "Calc 1"
    assert adapted.course.instructor == "Dr. Cohen"


# ===========================================================================
# TC-DTO-009: Test that ScheduleDTOAdapter raises ValueError for invalid date format.
# ===========================================================================
def test_schedule_dto_adapter_invalid_date():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "invalid-date-format", "FALL", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    
    # Act & Assert
    with pytest.raises(ValueError):
        ScheduleDTOAdapter(schedule)


# ===========================================================================
# TC-DTO-010: Test that ScheduleDTOAdapter raises ValueError for invalid Semester enum value.
# ===========================================================================
def test_schedule_dto_adapter_invalid_semester():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "NOT_A_SEMESTER", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    
    # Act & Assert
    with pytest.raises(ValueError):
        ScheduleDTOAdapter(schedule)


# ===========================================================================
# TC-DTO-011: Test that ScheduleDTOAdapter raises ValueError for invalid Moed enum value.
# ===========================================================================
def test_schedule_dto_adapter_invalid_moed():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "NOT_A_MOED")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    
    # Act & Assert
    with pytest.raises(ValueError):
        ScheduleDTOAdapter(schedule)


# ===========================================================================
# TC-DTO-012: Test that ScheduleDTOAdapter rejects extra attributes due to slots.
# ===========================================================================
def test_schedule_dto_adapter_rejects_extra_attributes():
    # Arrange
    schedule = ScheduleDTO(assignments=[], total_assignments=0)
    adapter = ScheduleDTOAdapter(schedule)
    
    # Act & Assert
    with pytest.raises(AttributeError):
        adapter.extra_attribute = "forbidden"


# ===========================================================================
# TC-DTO-013: Test that adapted assignment view rejects extra attributes due to slots.
# ===========================================================================
def test_adapted_assignment_view_rejects_extra_attributes():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    adapter = ScheduleDTOAdapter(schedule)
    adapted_assignment = adapter.assignments[0]
    
    # Act & Assert
    with pytest.raises(AttributeError):
        adapted_assignment.extra_attribute = "forbidden"


# ===========================================================================
# TC-DTO-014: Test that adapted course view rejects extra attributes due to slots.
# ===========================================================================
def test_adapted_course_view_rejects_extra_attributes():
    # Arrange
    a = AssignmentDTO("10101", "Calc 1", "Dr. Cohen", "2026-06-01", "FALL", "ALEPH")
    schedule = ScheduleDTO(assignments=[a], total_assignments=1)
    adapter = ScheduleDTOAdapter(schedule)
    adapted_course = adapter.assignments[0].course
    
    # Act & Assert
    with pytest.raises(AttributeError):
        adapted_course.extra_attribute = "forbidden"


# ===========================================================================
# TC-DTO-015: Test that ScheduleDTOAdapter correctly handles empty assignments list.
# ===========================================================================
def test_schedule_dto_adapter_empty_assignments():
    # Arrange
    schedule = ScheduleDTO(assignments=[], total_assignments=0)
    
    # Act
    adapter = ScheduleDTOAdapter(schedule)
    
    # Assert
    assert adapter.assignments == []


