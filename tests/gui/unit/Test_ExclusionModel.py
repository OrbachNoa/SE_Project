import pytest
from src.gui.common.components.ExclusionModel import ExclusionModel
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

# ===========================================================================
# TC-EXM-001: test constructor validation.
# ===========================================================================
def test_exclusion_model_init_validation():
    # Act & Assert
    with pytest.raises(ValueError, match="ExclusionModel requires at least one period"):
        ExclusionModel([])

# ===========================================================================
# TC-EXM-002: test model loads first period properties on init.
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
# TC-EXM-003: test toggle date addition (on).
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
# TC-EXM-004: test toggle date removal (off).
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
# TC-EXM-005: test navigation next automatically saves the current period.
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
# TC-EXM-006: test navigation previous automatically saves the current period.
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
# TC-EXM-007: test dates_between static helper for a standard range.
# ===========================================================================
def test_exclusion_model_dates_between_range():
    # Act
    dates = ExclusionModel.dates_between("2026-06-01", "2026-06-03")
    
    # Assert
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03"]

# ===========================================================================
# TC-EXM-008: test dates_between static helper for a single date.
# ===========================================================================
def test_exclusion_model_dates_between_single():
    # Act
    dates = ExclusionModel.dates_between("2026-06-01", "2026-06-01")
    
    # Assert
    assert dates == ["2026-06-01"]

# ===========================================================================
# TC-EXM-009: test dates_between static helper for an invalid range.
# ===========================================================================
def test_exclusion_model_dates_between_invalid():
    # Act
    dates = ExclusionModel.dates_between("2026-06-03", "2026-06-01")
    
    # Assert
    assert dates == []

# ===========================================================================
# TC-EXM-010: test date_list method.
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
# TC-EXM-011: test apply saves current period and returns viewmodels list.
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
