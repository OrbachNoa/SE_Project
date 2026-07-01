"""
Test suite for SelectedProgramIndex.

Scope   : Verifies construction (__init__, from_slots), program-membership
          checks (includes), per-course/per-slot entry lookups including the
          entries_for_slot fallback path, has_entries_for_course, and the
          slot-grouping methods (slots_by_program_year, slots_by_program,
          slots_by_program_year_semester_moed) together with the internal
          _group_slots caching behavior.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SPI-001, TC-SPI-002, ...
Fixtures: make_course, make_program_entry, make_period (shared); local slot
          builder helper to avoid depending on SlotBuilder internals.
"""
from datetime import date

from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex
from src.logic.SlotBuilder import Slot
from src.models.Enums import Semester, Moed, Requirement


def _make_slot(course, semester=Semester.FALL, moed=Moed.ALEPH, dates=None):
    """Build a bare Slot directly, without going through SlotBuilder."""
    return Slot(course=course, semester=semester, moed=moed, candidateDates=dates or [date(2026, 6, 1)])


# ---------------------------------------------------------------------------
# __init__ TC-SPI-001..003
# ---------------------------------------------------------------------------

# TC-SPI-001
# With no selected_programs given, includes() must accept every program id,
# since an empty filter means "no restriction".
def test_init_with_no_selected_programs_includes_every_program(make_course):
    # Arrange
    course = make_course(course_id="A")
    index = SelectedProgramIndex([course])

    # Act
    result = index.includes("83101")

    # Assert
    assert result is True
    assert index.selected_set is None


# TC-SPI-002
# With selected_programs given, entries_for_course must only contain program
# entries whose programId is in the selection -- unselected entries are
# filtered out entirely at construction time.
def test_init_filters_entries_by_selected_programs(make_course, make_program_entry):
    # Arrange
    pe_selected = make_program_entry(program_id="83101", year=1)
    pe_unselected = make_program_entry(program_id="83102", year=1)
    course = make_course(course_id="A", program_entries=[pe_selected, pe_unselected])

    # Act
    index = SelectedProgramIndex([course], selected_programs=["83101"])
    entries = index.entries_for_course("A")

    # Assert
    assert len(entries) == 1
    assert entries[0].programId == "83101"


# TC-SPI-003
# __init__ must also build the slot-keyed entries dict when slots are passed
# directly (not only via from_slots), so entries_for_slot works immediately.
def test_init_builds_entries_by_slot_when_slots_are_given(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, semester=Semester.FALL)
    course = make_course(course_id="A", program_entries=[pe])
    slot = _make_slot(course, semester=Semester.FALL)

    # Act
    index = SelectedProgramIndex([course], slots=[slot])
    entries = index.entries_for_slot(slot)

    # Assert
    assert len(entries) == 1
    assert entries[0].programId == "83101"


# ---------------------------------------------------------------------------
# from_slots TC-SPI-004..005
# ---------------------------------------------------------------------------

# TC-SPI-004
# from_slots must deduplicate courses by their first appearance in the slot
# list -- a course referenced by two slots contributes its program entries
# only once, not twice.
def test_from_slots_dedups_course_by_first_appearance(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course = make_course(course_id="A", program_entries=[pe])
    slot_one = _make_slot(course, moed=Moed.ALEPH)
    slot_two = _make_slot(course, moed=Moed.BET)

    # Act
    index = SelectedProgramIndex.from_slots([slot_one, slot_two])
    entries = index.entries_for_course("A")

    # Assert -- exactly one entry, not duplicated by the second slot.
    assert len(entries) == 1


# TC-SPI-005
# from_slots must build an index whose entries_for_course reflects each
# distinct course exactly once, in order of first appearance.
def test_from_slots_builds_index_with_each_distinct_course(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slot_a = _make_slot(course_a)
    slot_b = _make_slot(course_b)

    # Act
    index = SelectedProgramIndex.from_slots([slot_a, slot_b])

    # Assert
    assert index.has_entries_for_course("A") is True
    assert index.has_entries_for_course("B") is True


# ---------------------------------------------------------------------------
# includes() TC-SPI-006..007
# ---------------------------------------------------------------------------

# TC-SPI-006
# includes() must return True only for program ids inside the selection.
def test_includes_returns_true_only_for_selected_program(make_course):
    # Arrange
    index = SelectedProgramIndex([], selected_programs=["83101", "83102"])

    # Act & Assert
    assert index.includes("83101") is True
    assert index.includes("83103") is False


# TC-SPI-007
# includes() must return True for any program id when selected_programs is
# an empty list (falsy), matching the "no filter" semantics of None.
def test_includes_with_empty_selected_programs_list_includes_everything():
    # Arrange
    index = SelectedProgramIndex([], selected_programs=[])

    # Act
    result = index.includes("99999")

    # Assert
    assert result is True


# ---------------------------------------------------------------------------
# entries_for_course / entries_for_course_semester / entries_for_slot TC-SPI-008..011
# ---------------------------------------------------------------------------

# TC-SPI-008
# entries_for_course must return an empty tuple for a course id that was
# never indexed, instead of raising KeyError.
def test_entries_for_course_returns_empty_tuple_for_unknown_course():
    # Arrange
    index = SelectedProgramIndex([])

    # Act
    result = index.entries_for_course("UNKNOWN")

    # Assert
    assert result == ()


# TC-SPI-009
# entries_for_course_semester must only return entries matching the exact
# requested semester, excluding entries from other semesters of the same course.
def test_entries_for_course_semester_filters_by_semester(make_course, make_program_entry):
    # Arrange
    pe_fall = make_program_entry(program_id="83101", year=1, semester=Semester.FALL)
    pe_spring = make_program_entry(program_id="83101", year=1, semester=Semester.SPRI)
    course = make_course(course_id="A", program_entries=[pe_fall, pe_spring])
    index = SelectedProgramIndex([course])

    # Act
    fall_entries = index.entries_for_course_semester("A", Semester.FALL)
    spring_entries = index.entries_for_course_semester("A", Semester.SPRI)

    # Assert
    assert len(fall_entries) == 1
    assert fall_entries[0].semester == Semester.FALL
    assert len(spring_entries) == 1
    assert spring_entries[0].semester == Semester.SPRI


# TC-SPI-010
# entries_for_slot must use the prebuilt per-slot dict when the slot object
# was part of the slots used at construction time.
def test_entries_for_slot_uses_prebuilt_dict_for_known_slot(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, semester=Semester.FALL)
    course = make_course(course_id="A", program_entries=[pe])
    slot = _make_slot(course, semester=Semester.FALL)
    index = SelectedProgramIndex([course], slots=[slot])

    # Act
    result = index.entries_for_slot(slot)

    # Assert
    assert len(result) == 1
    assert result[0].programId == "83101"


# TC-SPI-011
# entries_for_slot must fall back to entries_for_course_semester when the
# slot was NOT part of the slots given at construction time (so it is absent
# from the prebuilt _entries_by_slot dict), rather than returning empty.
def test_entries_for_slot_falls_back_for_slot_not_in_prebuilt_dict(make_course, make_program_entry):
    # Arrange -- index built with no slots at all, so _entries_by_slot is empty.
    pe = make_program_entry(program_id="83101", year=2, semester=Semester.FALL)
    course = make_course(course_id="A", program_entries=[pe])
    index = SelectedProgramIndex([course])
    late_slot = _make_slot(course, semester=Semester.FALL)

    # Act
    result = index.entries_for_slot(late_slot)

    # Assert -- the fallback still finds the course/semester match.
    assert len(result) == 1
    assert result[0].programId == "83101"


# ---------------------------------------------------------------------------
# has_entries_for_course TC-SPI-012..013
# ---------------------------------------------------------------------------

# TC-SPI-012
# has_entries_for_course must return True when the course has at least one
# selected entry.
def test_has_entries_for_course_true_when_entries_exist(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course = make_course(course_id="A", program_entries=[pe])
    index = SelectedProgramIndex([course])

    # Act
    result = index.has_entries_for_course("A")

    # Assert
    assert result is True


# TC-SPI-013
# has_entries_for_course must return False when a course's only program
# entry is filtered out by the selected-programs restriction.
def test_has_entries_for_course_false_when_filtered_out(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83102", year=2)
    course = make_course(course_id="A", program_entries=[pe])
    index = SelectedProgramIndex([course], selected_programs=["83101"])

    # Act
    result = index.has_entries_for_course("A")

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# slots_by_program_year / slots_by_program / slots_by_program_year_semester_moed
# TC-SPI-014..017
# ---------------------------------------------------------------------------

# TC-SPI-014
# slots_by_program_year must group slots under (programId, year) keys built
# from each slot's course's selected program entries.
def test_slots_by_program_year_groups_by_program_and_year(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course = make_course(course_id="A", program_entries=[pe])
    slot = _make_slot(course)
    index = SelectedProgramIndex.from_slots([slot])

    # Act
    groups = index.slots_by_program_year()

    # Assert
    assert groups == {("83101", 2): {slot}}


# TC-SPI-015
# slots_by_program must group slots under the bare programId key, ignoring
# year -- two different years of the same program collapse into one group.
def test_slots_by_program_groups_by_program_ignoring_year(make_course, make_program_entry):
    # Arrange
    pe_year_one = make_program_entry(program_id="83101", year=1)
    pe_year_two = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe_year_one])
    course_b = make_course(course_id="B", program_entries=[pe_year_two])
    slot_a = _make_slot(course_a)
    slot_b = _make_slot(course_b)
    index = SelectedProgramIndex.from_slots([slot_a, slot_b])

    # Act
    groups = index.slots_by_program()

    # Assert
    assert groups == {"83101": {slot_a, slot_b}}


# TC-SPI-016
# slots_by_program_year_semester_moed must use entries_for_slot (semester
# aware) and group by (programId, year, slot.semester, slot.moed).
def test_slots_by_program_year_semester_moed_groups_with_full_key(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, semester=Semester.FALL)
    course = make_course(course_id="A", program_entries=[pe])
    slot = _make_slot(course, semester=Semester.FALL, moed=Moed.BET)
    index = SelectedProgramIndex.from_slots([slot])

    # Act
    groups = index.slots_by_program_year_semester_moed()

    # Assert
    assert groups == {("83101", 2, Semester.FALL, Moed.BET): {slot}}


# TC-SPI-017
# A requirement filter passed to the grouping methods must exclude entries
# whose requirement does not match -- an ELECTIVE entry must not appear when
# filtering for OBLIGATORY.
def test_slots_by_program_year_filters_by_requirement(make_course, make_program_entry):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83102", year=3, requirement=Requirement.ELECTIVE)
    course_obligatory = make_course(course_id="A", program_entries=[pe_obligatory])
    course_elective = make_course(course_id="B", program_entries=[pe_elective])
    slot_obligatory = _make_slot(course_obligatory)
    slot_elective = _make_slot(course_elective)
    index = SelectedProgramIndex.from_slots([slot_obligatory, slot_elective])

    # Act
    groups = index.slots_by_program_year(requirement=Requirement.OBLIGATORY)

    # Assert
    assert groups == {("83101", 2): {slot_obligatory}}


# ---------------------------------------------------------------------------
# _group_slots caching behavior TC-SPI-018..020
# ---------------------------------------------------------------------------

# TC-SPI-018
# Calling slots_by_program_year() twice with the default (cached) slots must
# return equal results, proving the cache does not corrupt or lose data
# across repeated calls.
def test_group_slots_cache_returns_consistent_results_across_calls(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course = make_course(course_id="A", program_entries=[pe])
    slot = _make_slot(course)
    index = SelectedProgramIndex.from_slots([slot])

    # Act
    first_call = index.slots_by_program_year()
    second_call = index.slots_by_program_year()

    # Assert
    assert first_call == second_call
    assert first_call == {("83101", 2): {slot}}


# TC-SPI-019
# The cache must be keyed separately per requirement filter -- a call with
# requirement=OBLIGATORY must not return the cached result of a prior
# no-filter call.
def test_group_slots_cache_is_keyed_by_requirement(make_course, make_program_entry):
    # Arrange
    pe_obligatory = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe_elective = make_program_entry(program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    course_obligatory = make_course(course_id="A", program_entries=[pe_obligatory])
    course_elective = make_course(course_id="B", program_entries=[pe_elective])
    slot_obligatory = _make_slot(course_obligatory)
    slot_elective = _make_slot(course_elective)
    index = SelectedProgramIndex.from_slots([slot_obligatory, slot_elective])

    # Act
    unfiltered = index.slots_by_program_year()
    obligatory_only = index.slots_by_program_year(requirement=Requirement.OBLIGATORY)

    # Assert
    assert unfiltered == {("83101", 2): {slot_obligatory, slot_elective}}
    assert obligatory_only == {("83101", 2): {slot_obligatory}}


# TC-SPI-020
# Passing an explicit slots= override must bypass the cache entirely and
# compute fresh groups for only the given slots, ignoring the slots stored
# at construction time.
def test_group_slots_explicit_slots_override_bypasses_cache(make_course, make_program_entry):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    slot_a = _make_slot(course_a)
    slot_b = _make_slot(course_b)
    # Index built from both slots, so the cached (no-arg) result includes both.
    index = SelectedProgramIndex.from_slots([slot_a, slot_b])
    cached_result = index.slots_by_program_year()

    # Act -- explicit override restricts the grouping to slot_a only.
    overridden_result = index.slots_by_program_year(slots=[slot_a])

    # Assert
    assert cached_result == {("83101", 2): {slot_a, slot_b}}
    assert overridden_result == {("83101", 2): {slot_a}}
