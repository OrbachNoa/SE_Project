import pytest
from src.application.services.ViewModelMapper import ViewModelMapper
from src.application.dto.ScheduleDTO import ScheduleDTO, AssignmentDTO
from src.models.Course import Course
from src.models.Enums import EvalType, Semester, Requirement, Moed
from src.models.ExamPeriod import ExamPeriod
from datetime import date

# -----------------------------------------------------------------
# to_schedule_vm() - TC-VM-001..003
# -----------------------------------------------------------------

# ===========================================================================
# TC-VM-001: test that an empty schedule is mapped to an empty view model.
# ===========================================================================
def test_viewmodel_mapper_to_schedule_vm_empty():
    # Arrange
    mapper = ViewModelMapper()
    dto = ScheduleDTO(assignments=[], total_assignments=0)

    # Act
    vm = mapper.to_schedule_vm(dto, current_index=0, total=0)

    # Assert
    assert vm.current_index == 0
    assert vm.total == 0
    assert vm.is_empty() is True
    assert len(vm.items) == 0

# ===========================================================================
# TC-VM-002: test that a schedule with items is mapped to a non-empty view model.
# ===========================================================================
def test_viewmodel_mapper_to_schedule_vm_with_items(make_assignment_dto):
    # Arrange
    mapper = ViewModelMapper()
    a = make_assignment_dto(course_id="10101", course_name="Calculus 1", date="2026-06-05")
    # Add program requirements
    a.program_requirements = [("83101", "OBLIGATORY")]
    dto = ScheduleDTO(assignments=[a], total_assignments=1)

    # Act
    vm = mapper.to_schedule_vm(dto, current_index=0, total=1, selected_programs=["83101"])

    # Assert
    assert vm.current_index == 0
    assert vm.total == 1
    assert vm.is_empty() is False
    assert len(vm.items) == 1
    item = vm.items[0]
    assert item.date == "2026-06-05"
    assert item.title == "Calculus 1"
    assert "Program 83101: Obligatory" in item.tooltip


# ===========================================================================
# TC-VM-003: test that the view model mapper raises a value error when the schedule DTO is None.
# ===========================================================================
def test_viewmodel_mapper_to_schedule_vm_none_raises_value_error():
    # Arrange
    mapper = ViewModelMapper()

    # Act & Assert
    with pytest.raises(ValueError):
        mapper.to_schedule_vm(None)


# ===========================================================================
# TC-VM-004: test that the view model mapper filters the assignments by program.
# ===========================================================================
@pytest.mark.parametrize("selected_programs, expected_in, expected_not_in", [
    # Case A: Filtered selection includes only one program
    (["83101"], ["Program 83101: Obligatory"], ["Program 83102"]),
    # Case B: Filtered selection has no overlap (empty program block)
    (["83103"], [], ["Program"]),
    # Case C: Filtered selection is None (acts as bypass/default to show all)
    (None, ["Program 83101: Obligatory", "Program 83102: Elective"], [])
])
def test_viewmodel_mapper_tooltip_filtering(make_assignment_dto, selected_programs, expected_in, expected_not_in):
    # Arrange
    mapper = ViewModelMapper()
    a = make_assignment_dto(course_id="10101", course_name="Calculus 1", date="2026-06-05")
    a.program_requirements = [
        ("83101", "OBLIGATORY"),
        ("83102", "ELECTIVE")
    ]
    dto = ScheduleDTO(assignments=[a], total_assignments=1)

    # Act
    vm = mapper.to_schedule_vm(dto, selected_programs=selected_programs)
    tooltip = vm.items[0].tooltip

    # Assert
    for substring in expected_in:
        assert substring in tooltip
    for substring in expected_not_in:
        assert substring not in tooltip



# ===========================================================================
# TC-VM-005: test that the view model mapper sorts the assignments by date.
# ===========================================================================
def test_viewmodel_mapper_to_schedule_vm_date_sorting(make_assignment_dto):
    # Arrange
    mapper = ViewModelMapper()
    a1 = make_assignment_dto(course_id="10101", date="2026-06-10")
    a2 = make_assignment_dto(course_id="10102", date="2026-06-01")
    a3 = make_assignment_dto(course_id="10103", date="2026-06-05")
    dto = ScheduleDTO(assignments=[a1, a2, a3], total_assignments=3)

    # Act
    vm = mapper.to_schedule_vm(dto)

    # Assert - should be sorted chronologically by date
    assert vm.items[0].date == "2026-06-01"
    assert vm.items[1].date == "2026-06-05"
    assert vm.items[2].date == "2026-06-10"


# -----------------------------------------------------------------
# to_program_vms() - TC-VM-006..007
# -----------------------------------------------------------------

# ===========================================================================
# TC-VM-006: test that the view model mapper converts a list of courses into a list of program view models.
# ===========================================================================
def test_viewmodel_mapper_to_program_view_models(make_course):
    # Arrange
    mapper = ViewModelMapper()
    c = make_course()
    courses = [c]

    # Act
    vms = mapper.to_program_vms(courses)

    # Assert
    assert len(vms) > 0
    assert vms[0].program_id == "83101"


# ===========================================================================
# TC-VM-007: test that the view model mapper filters the programs by evaluation type.
# ===========================================================================
def test_viewmodel_mapper_to_program_vms_filtering_and_sorting(make_course, make_program_entry):
    # Arrange
    mapper = ViewModelMapper()
    
    # Program 83102 has 1 exam course and 1 project course
    p2 = make_program_entry(program_id="83102")
    c1 = make_course(course_id="201", evaluation=EvalType.EXAM, program_entries=[p2])
    c2 = make_course(course_id="202", evaluation=EvalType.PROJECT, program_entries=[p2])
    
    # Program 83101 has 1 exam course
    p1 = make_program_entry(program_id="83101")
    c3 = make_course(course_id="101", evaluation=EvalType.EXAM, program_entries=[p1])

    # Act
    vms = mapper.to_program_vms([c1, c2, c3])

    # Assert - should be sorted by program_id
    assert len(vms) == 2
    assert vms[0].program_id == "83101"
    assert vms[0].course_count == 1  # c3 is EXAM
    
    assert vms[1].program_id == "83102"
    assert vms[1].course_count == 1  # c1 is EXAM, c2 is PROJECT (non-exam ignored)

# -----------------------------------------------------------------
# to_program_courses_vm() - TC-VM-008..009
# -----------------------------------------------------------------


# ===========================================================================
# TC-VM-008: test that the view model mapper converts a list of courses into a list of program courses view models.
# ===========================================================================
def test_viewmodel_mapper_to_program_courses_vm(make_course):
    # Arrange
    mapper = ViewModelMapper()
    c = make_course()
    courses = [c]

    # Act
    vms = mapper.to_program_courses_vm(courses)

    # Assert
    assert len(vms) > 0
    assert vms[0].program_id == "83101"
    assert len(vms[0].courses) == 1

# ===========================================================================
# TC-VM-009: test that the view model mapper sorts the program courses by program ID.
# ===========================================================================
def test_viewmodel_mapper_to_program_courses_vm_multi_program_and_sorting(make_course, make_program_entry):
    # Arrange
    mapper = ViewModelMapper()
    
    p1 = make_program_entry(program_id="83101")
    p2 = make_program_entry(program_id="83102")
    
    # c1 belongs to both programs 83101 and 83102
    c1 = make_course(course_id="102", program_entries=[p1, p2])
    # c2 belongs to 83101 only
    c2 = make_course(course_id="101", program_entries=[p1])

    # Act
    vms = mapper.to_program_courses_vm([c1, c2])

    # Assert - sorted by program_id
    assert len(vms) == 2
    
    # Program 83101
    assert vms[0].program_id == "83101"
    # courses inside should be sorted by course_id: 101, then 102
    assert len(vms[0].courses) == 2
    assert vms[0].courses[0].course_id == "101"
    assert vms[0].courses[1].course_id == "102"
    
    # Program 83102
    assert vms[1].program_id == "83102"
    assert len(vms[1].courses) == 1
    assert vms[1].courses[0].course_id == "102"


# -----------------------------------------------------------------
# to_calendar_vm() - TC-VM-010..012
# -----------------------------------------------------------------


# ===========================================================================
# TC-VM-010: test that the view model mapper converts a schedule DTO into a calendar view model.
# ===========================================================================
def test_viewmodel_mapper_to_calendar_vm(make_assignment_dto):
    # Arrange
    mapper = ViewModelMapper()
    a1 = make_assignment_dto(course_id="10101", course_name="Calculus 1", date="2026-06-05")
    a2 = make_assignment_dto(course_id="10102", course_name="Linear Algebra", date="2026-06-05")
    a3 = make_assignment_dto(course_id="10103", course_name="Physics", date="2026-06-06")
    dto = ScheduleDTO(assignments=[a1, a2, a3], total_assignments=3)

    # Act
    vm = mapper.to_calendar_vm(dto)

    # Assert
    assert len(vm.cells) == 2
    assert vm.cells[0].date == "2026-06-05"
    assert vm.cells[0].tooltip == "2 exams"
    assert len(vm.cells[0].items) == 2

    assert vm.cells[1].date == "2026-06-06"
    assert vm.cells[1].tooltip == "1 exam"
    assert len(vm.cells[1].items) == 1


# ===========================================================================
# TC-VM-011: test that to_calendar_vm raises a ValueError when the schedule DTO is None.
# ===========================================================================
def test_viewmodel_mapper_to_calendar_vm_none_raises_value_error():
    # Arrange
    mapper = ViewModelMapper()

    # Act & Assert
    with pytest.raises(ValueError):
        mapper.to_calendar_vm(None)


# -----------------------------------------------------------------
# to_period_edit_vms() - TC-VM-013..014
# -----------------------------------------------------------------

# ===========================================================================
# TC-VM-013: test that the view model mapper converts a list of periods into a list of period edit view models.
# ===========================================================================
def test_viewmodel_mapper_to_period_edit_vms(make_period):
    # Arrange
    mapper = ViewModelMapper()
    p1 = make_period(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start=date(2026, 6, 1),
        end=date(2026, 6, 15),
        excluded=[date(2026, 6, 5)]
    )
    p2 = make_period(
        semester=Semester.SPRI,
        moed=Moed.BET,
        start=date(2026, 7, 1),
        end=date(2026, 7, 20)
    )

    # Act
    vms = mapper.to_period_edit_vms([p1, p2])

    # Assert
    assert len(vms) == 2
    assert vms[0].semester == "FALL"
    assert vms[0].moed == "ALEPH"
    assert vms[0].start_date == "2026-06-01"
    assert vms[0].end_date == "2026-06-15"
    assert vms[0].excluded_dates == ["2026-06-05"]

    assert vms[1].semester == "SPRI"
    assert vms[1].moed == "BET"
    assert vms[1].start_date == "2026-07-01"
    assert vms[1].end_date == "2026-07-20"
    assert vms[1].excluded_dates == []


# ===========================================================================
# TC-VM-014: test that to_period_edit_vms returns an empty list when periods is None.
# ===========================================================================
def test_viewmodel_mapper_to_period_edit_vms_none_returns_empty_list():
    # Arrange
    mapper = ViewModelMapper()

    # Act & Assert
    assert mapper.to_period_edit_vms(None) == []
