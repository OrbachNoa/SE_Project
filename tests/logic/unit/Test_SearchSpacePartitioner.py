"""
Test suite for SearchSpacePartitioner and WorkUnit.

Scope   : Verifies SearchSpacePartitioner.partition() against an empty slot
          list, a small realistic slot list that splits into the desired
          number of units with plausible seed_dates, and the pruning of dead
          units (seeds whose continuation has zero valid children). Also
          covers WorkUnit as a small frozen dataclass: construction and
          field access.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SSP-001, TC-SSP-002, ...
Fixtures: make_course, make_program_entry, make_period (shared)
"""
from datetime import date
import pytest

from src.logic.SlotBuilder import SlotBuilder
from src.logic.checkers.MinDaysBetweenExamsChecker import GapScope, MinDaysBetweenExamsChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.parallel.SearchSpacePartitioner import SearchSpacePartitioner
from src.logic.parallel.WorkUnit import WorkUnit
from src.models.Enums import Requirement


def _default_checkers(courses):
    """Build the two always-on checkers, prepared and ready for use."""
    program_checker = ProgramYearConflictChecker()
    program_checker.precompute_conflicts(courses)
    return [program_checker, MoedOrderChecker()]


# ---------------------------------------------------------------------------
# WorkUnit TC-SSP-001..002
# ---------------------------------------------------------------------------

# TC-SSP-001
# A WorkUnit must store its seed_dates tuple exactly as given and expose it
# through the seed_dates attribute.
def test_work_unit_stores_seed_dates_as_given():
    # Arrange
    dates = (date(2026, 6, 1), date(2026, 6, 5))

    # Act
    unit = WorkUnit(seed_dates=dates)

    # Assert
    assert unit.seed_dates == (date(2026, 6, 1), date(2026, 6, 5))


# TC-SSP-002
# WorkUnit is a frozen dataclass, so reassigning seed_dates after
# construction must raise rather than silently mutate the unit.
def test_work_unit_is_immutable():
    # Arrange
    unit = WorkUnit(seed_dates=(date(2026, 6, 1),))

    # Act & Assert
    with pytest.raises(Exception):
        unit.seed_dates = (date(2026, 6, 9),)
    assert unit.seed_dates == (date(2026, 6, 1),)


# ---------------------------------------------------------------------------
# SearchSpacePartitioner.partition() TC-SSP-003..007
# ---------------------------------------------------------------------------

# TC-SSP-003
# partition() with an empty slot list must return an empty list immediately
# -- there is no search space to split.
def test_partition_with_empty_slots_returns_empty_list():
    # Arrange
    partitioner = SearchSpacePartitioner(checkers=[])

    # Act
    result = partitioner.partition([], desired_units=4)

    # Assert
    assert result == []


# TC-SSP-004
# A small, conflict-free slot list (two obligatory courses, three open
# dates) must split into exactly the requested number of units, with each
# unit's seed_dates drawn from the real candidate dates of the slots.
def test_partition_splits_small_slot_list_into_desired_unit_count(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[])
    slots = SlotBuilder([period]).build([course_a, course_b])
    checkers = _default_checkers([course_a, course_b])
    partitioner = SearchSpacePartitioner(checkers)
    possible_dates = set(period.availableDates)

    # Act
    units = partitioner.partition(slots, desired_units=4)

    # Assert
    assert len(units) == 4
    for unit in units:
        assert 1 <= len(unit.seed_dates) <= len(slots)
        assert all(d in possible_dates for d in unit.seed_dates)


# TC-SSP-005
# Requesting only one unit must return the first real frontier produced from
# splitting the very first slot -- one unit per candidate date of slot 0,
# without further splitting since the frontier already reached the target.
def test_partition_with_desired_units_one_returns_first_frontier(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[])
    slots = SlotBuilder([period]).build([course_a, course_b])
    checkers = _default_checkers([course_a, course_b])
    partitioner = SearchSpacePartitioner(checkers)

    # Act
    units = partitioner.partition(slots, desired_units=1)

    # Assert -- three open dates for the first slot, none excluded by the
    # base checkers, so the first frontier already has three depth-1 units.
    assert len(units) == 3
    assert all(len(unit.seed_dates) == 1 for unit in units)


# TC-SSP-006
# When a minimum-gap rule kills off some partial schedules (a seed date that
# leaves no room for the required gap), partition() must prune those dead
# units instead of returning them as part of the frontier -- the result must
# never include more units than the number of seeds that actually have at
# least one valid continuation.
def test_partition_prunes_dead_units_with_no_valid_children(
    make_course, make_program_entry, make_period,
):
    # Arrange -- two obligatory courses needing a 2-day gap, but only three
    # candidate dates one day apart: seeding the middle date (June 2) leaves
    # no remaining date at least 2 days away, so that branch is dead.
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="A", program_entries=[pe])
    course_b = make_course(course_id="B", program_entries=[pe])
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[])
    slots = SlotBuilder([period]).build([course_a, course_b])

    program_checker = ProgramYearConflictChecker()
    program_checker.precompute_conflicts([course_a, course_b])
    gap_checker = MinDaysBetweenExamsChecker(GapScope.OBLIGATORY_ONLY, 2)
    gap_checker.prepare([course_a, course_b])
    checkers = [program_checker, MoedOrderChecker(), gap_checker]
    partitioner = SearchSpacePartitioner(checkers)

    # Act
    units = partitioner.partition(slots, desired_units=4)

    # Assert -- only the June-1 and June-3 seeds have a valid second date;
    # the June-2 seed is dead and must be pruned, so we get exactly 2 units
    # even though 4 were requested.
    assert len(units) == 2
    for unit in units:
        assert len(unit.seed_dates) == 2
        assert abs((unit.seed_dates[1] - unit.seed_dates[0]).days) >= 2


# TC-SSP-007
# Every WorkUnit produced by partition() must have a seed_dates tuple with
# no duplicate dates within itself, since each seed date corresponds to a
# distinct slot in the same partial schedule.
def test_partition_produced_units_have_no_duplicate_seed_dates(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    courses = [make_course(course_id=cid, program_entries=[pe]) for cid in ("A", "B", "C")]
    period = make_period(start=date(2026, 6, 1), end=date(2026, 6, 5), excluded=[])
    slots = SlotBuilder([period]).build(courses)
    checkers = _default_checkers(courses)
    partitioner = SearchSpacePartitioner(checkers)

    # Act
    units = partitioner.partition(slots, desired_units=6)

    # Assert
    assert len(units) > 0
    for unit in units:
        assert len(set(unit.seed_dates)) == len(unit.seed_dates)
