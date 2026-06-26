"""Unit tests for ExclusionModel — the calendar editor's per-period state.

The model wraps a list of PeriodEditViewModel objects and tracks which one
is currently being edited. Navigating to another period auto-saves the
in-memory edits (date range, excluded dates) on the period being left,
before switching — the screen never needs an explicit "save" step between
periods. Tests cover construction validation, initial state, date-exclusion
toggling, the auto-save-on-navigate behaviour in both directions, the
dates_between() helper's boundary cases, and apply().

Conventions:
- Each test carries a unique TC-EXM-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections, except
  where the assertion is itself the pytest.raises context manager.
- No conftest fixture models PeriodEditViewModel or ExclusionModel, so
  every test builds them directly; this is a plain Python class with no
  Qt dependency, so no `qapp` fixture is needed either.
"""
import pytest
from src.gui.common.components.ExclusionModel import ExclusionModel
from src.gui.common.helpers import dates_between
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-EXM-001: constructing with an empty period list must raise — there is
# no valid "no periods" state for the editor to fall back to.
# ===========================================================================
def test_exclusion_model_init_validation():
    # Act & Assert
    with pytest.raises(ValueError, match="ExclusionModel requires at least one period"):
        ExclusionModel([])

# ===========================================================================
# TC-EXM-002: construction must load the first period's date range and
# excluded dates immediately, with excluded_dates exposed as a set.
# ===========================================================================
def test_exclusion_model_loads_first_period():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=["2026-06-02"]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    
    # Act
    model = ExclusionModel(vms)
    
    # Assert
    assert model.current_index == 0
    assert model.total == 2
    assert model.current_period == vms[0]
    assert model.start_date == "2026-06-01"
    assert model.end_date == "2026-06-03"
    assert model.excluded_dates == {"2026-06-02"}

# ===========================================================================
# TC-EXM-003: toggling a date not yet excluded must add it and report
# True (the new excluded state), so the UI knows which style to apply.
# ===========================================================================
def test_exclusion_model_toggle_date_on():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    model = ExclusionModel(vms)
    
    # Act
    res = model.toggle("2026-06-02")
    
    # Assert
    assert res is True
    assert "2026-06-02" in model.excluded_dates

# ===========================================================================
# TC-EXM-004: toggling an already-excluded date must remove it and report
# False — the toggle has to be reversible, not a one-way add.
# ===========================================================================
def test_exclusion_model_toggle_date_off():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=["2026-06-02"]
        )
    ]
    model = ExclusionModel(vms)
    
    # Act
    res = model.toggle("2026-06-02")
    
    # Assert
    assert res is False
    assert "2026-06-02" not in model.excluded_dates

# ===========================================================================
# TC-EXM-005: move_next() must write the in-memory edits (date range,
# excluded dates) back onto the period being left, before switching — the
# screen has no separate "save" button between periods.
# ===========================================================================
def test_exclusion_model_navigation_next_saves_state():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    model = ExclusionModel(vms)
    assert model.can_move_previous() is False
    assert model.can_move_next() is True
    
    # Modify details in memory
    model.set_date_range("2026-06-02", "2026-06-03")
    model.toggle("2026-06-03")
    
    # Act
    model.move_next()
    
    # Assert
    assert model.current_index == 1
    assert model.current_period == vms[1]
    assert model.can_move_previous() is True
    assert model.can_move_next() is False
    # Verify first viewmodel was auto-saved
    assert vms[0].start_date == "2026-06-02"
    assert vms[0].excluded_dates == ["2026-06-03"]

# ===========================================================================
# TC-EXM-006: move_previous() must auto-save just like move_next() — the
# save-on-navigate behaviour is symmetric in both directions.
# ===========================================================================
def test_exclusion_model_navigation_previous_saves_state():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    model = ExclusionModel(vms)
    model.move_next()
    
    # Modify second period in memory
    model.toggle("2026-07-02")
    
    # Act
    model.move_previous()
    
    # Assert
    assert model.current_index == 0
    # Verify second viewmodel was auto-saved
    assert vms[1].excluded_dates == ["2026-07-02"]

# ===========================================================================
# TC-EXM-007: dates_between() must enumerate every calendar date from start
# to end inclusive — the editor grid needs one cell per date in range.
# ===========================================================================
def test_exclusion_model_dates_between_range():
    # Act
    dates = dates_between("2026-06-01", "2026-06-03")
    
    # Assert
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03"]

# ===========================================================================
# TC-EXM-008: a one-day range (start == end) must return that single date,
# not an empty list — the inclusive-range logic must not off-by-one here.
# ===========================================================================
def test_exclusion_model_dates_between_single():
    # Act
    dates = dates_between("2026-06-01", "2026-06-01")
    
    # Assert
    assert dates == ["2026-06-01"]

# ===========================================================================
# TC-EXM-009: an inverted range (start after end) must return an empty
# list rather than raising or iterating backwards.
# ===========================================================================
def test_exclusion_model_dates_between_invalid():
    # Act
    dates = dates_between("2026-06-03", "2026-06-01")
    
    # Assert
    assert dates == []

# ===========================================================================
# TC-EXM-010: date_list() must expose the current period's full date range
# (via dates_between) so the editor can render one cell per date.
# ===========================================================================
def test_exclusion_model_date_list():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-02",
            excluded_dates=[]
        )
    ]
    model = ExclusionModel(vms)
    
    # Act
    dates = model.date_list()
    
    # Assert
    assert dates == ["2026-06-01", "2026-06-02"]

# ===========================================================================
# TC-EXM-011: apply() must save the current period's edits and return the
# full view-model list — the caller needs the saved data back to persist it.
# ===========================================================================
def test_exclusion_model_apply():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    model = ExclusionModel(vms)
    model.toggle("2026-06-02")
    
    # Act
    res = model.apply()
    
    # Assert
    assert res == vms
    assert vms[0].excluded_dates == ["2026-06-02"]
