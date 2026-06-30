"""
Test suite for ScheduleExportService.

Scope   : save() creating the parent directory before delegating to the
          injected writer's write() with an adapted DTO, and format()
          delegating to the writer's formatSchedule().
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SES-001 .. TC-SES-004
Fixtures: tmp_path (pytest built-in), make_assignment_dto, make_schedule_dto
          (tests/conftest.py)
"""
from unittest.mock import MagicMock

from src.application.dto.ScheduleDTOAdapter import ScheduleDTOAdapter
from src.application.services.ScheduleExportService import ScheduleExportService


# TC-SES-001
# save() must create any missing parent directories for the target path
# before writing, so a user-chosen path from a file dialog whose directory
# does not yet exist on disk does not fail mid-write.
def test_save_creates_missing_parent_directory(tmp_path, make_schedule_dto):
    # Arrange
    writer = MagicMock()
    service = ScheduleExportService(writer)
    schedule_dto = make_schedule_dto()
    target_path = tmp_path / "nested" / "deeper" / "schedule.txt"

    # Act
    service.save(schedule_dto, str(target_path))

    # Assert
    assert target_path.parent.exists()
    assert target_path.parent.is_dir()


# TC-SES-002
# save() must delegate to the writer's write() with a single-element list
# containing a ScheduleDTOAdapter wrapping the given DTO, and the exact path.
def test_save_delegates_to_writer_with_adapted_dto(tmp_path, make_schedule_dto, make_assignment_dto):
    # Arrange
    writer = MagicMock()
    service = ScheduleExportService(writer)
    assignment = make_assignment_dto()
    schedule_dto = make_schedule_dto(assignments=[assignment])
    target_path = tmp_path / "out.txt"

    # Act
    service.save(schedule_dto, str(target_path))

    # Assert
    writer.write.assert_called_once()
    written_schedules, written_path = writer.write.call_args[0]
    assert written_path == str(target_path)
    assert len(written_schedules) == 1
    assert isinstance(written_schedules[0], ScheduleDTOAdapter)
    assert written_schedules[0].assignments[0].course.name == assignment.course_name


# TC-SES-003
# save() must not swallow an existing directory — re-saving to the same
# path twice must not raise even though the parent already exists.
def test_save_does_not_raise_when_parent_directory_already_exists(tmp_path, make_schedule_dto):
    # Arrange
    writer = MagicMock()
    service = ScheduleExportService(writer)
    schedule_dto = make_schedule_dto()
    target_path = tmp_path / "out.txt"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Act
    service.save(schedule_dto, str(target_path))
    service.save(schedule_dto, str(target_path))

    # Assert
    assert writer.write.call_count == 2


# TC-SES-004
# format() must delegate to the writer's formatSchedule() with an adapted
# DTO and return exactly the writer's output, unmodified.
def test_format_delegates_to_writer_format_schedule(make_schedule_dto, make_assignment_dto):
    # Arrange
    writer = MagicMock()
    writer.formatSchedule.return_value = "=== Exam System Option 1 ===\nCalculus 1\n"
    service = ScheduleExportService(writer)
    assignment = make_assignment_dto()
    schedule_dto = make_schedule_dto(assignments=[assignment])

    # Act
    result = service.format(schedule_dto)

    # Assert
    assert result == "=== Exam System Option 1 ===\nCalculus 1\n"
    writer.formatSchedule.assert_called_once()
    adapted_arg = writer.formatSchedule.call_args[0][0]
    assert isinstance(adapted_arg, ScheduleDTOAdapter)
    assert adapted_arg.assignments[0].course.name == assignment.course_name
