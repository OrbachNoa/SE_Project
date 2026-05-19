from unittest.mock import MagicMock
import pytest

from src.validators.maxProgramsValidator import MaxProgramsValidator
from src.validators.programExistenceValidator import ProgramExistenceValidator
from src.validators.inputValidator import InputValidator


# ---------------------------------------------------------------------------
# MaxProgramsValidator — TC-VAL-001..004 (boundary value tests)
# ---------------------------------------------------------------------------

# TC-VAL-001: Exactly 5 programs (the upper boundary) must be accepted.
def test_max_programs_validator_accepts_exactly_five(make_program_entry):
    # Arrange — 5 distinct program entries, codes 83101..83105.
    selected = [f"8310{i}" for i in range(1, 6)]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is True


# TC-VAL-002: 6 programs (one over the max) must be rejected.
def test_max_programs_validator_rejects_six(make_program_entry):
    # Arrange — 6 distinct program entries.
    selected = [f"8310{i}" for i in range(1, 7)]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is False


# TC-VAL-003: 1 program (the minimum viable input) must be accepted.
def test_max_programs_validator_accepts_one(make_program_entry):
    # Arrange — exactly one program entry.
    selected = ["83101"]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is True


# TC-VAL-004: 0 programs (empty selection) must be rejected.
# The system cannot schedule anything with no programs selected.
def test_max_programs_validator_rejects_zero():
    # Arrange — empty selection.
    selected = []
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# ProgramExistenceValidator — TC-VAL-005..007
# ---------------------------------------------------------------------------

# TC-VAL-005: When every selected program code is present in the master list, the validator must return True. 
def test_program_existence_validator_accepts_when_all_in_master(make_program_entry):
    # Arrange
    master = ["83101", "83102", "83103"]
    selected = ["83101", "83102"]
    # Act
    result = ProgramExistenceValidator().validate(selected, master)
    # Assert
    assert result is True


# TC-VAL-006: A single unknown program code must cause the validator to return false.
def test_program_existence_validator_rejects_unknown_code(make_program_entry):
    # Arrange — '99999' is not in the master list.
    master = ["83101", "83102"]
    selected = ["83101", "99999"]
    # Act
    result = ProgramExistenceValidator().validate(selected, master)
    # Assert
    assert result is False


# TC-VAL-007: Substring/prefix matching is NOT allowed — '8310' is not a valid match for '83101'.
def test_program_existence_validator_rejects_prefix_match(make_program_entry):
    # Arrange — '8310' is a prefix of '83101' but not equal to it.
    master = ["83101"]
    selected = ["8310"]
    # Act
    try:
        result = ProgramExistenceValidator().validate(selected, master)
    except ValueError:
        result = False

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# TC-VAL-008 — Validator failure halts the pipeline before Phase 3.
# This is the critical architectural test that mirrors the sequence
# diagram's Phase 2 'alt' branch: when validation fails, the scheduler
# must not be invoked at all.
# ---------------------------------------------------------------------------

# TC-VAL-008: When any IInputValidator returns False, the orchestration
# must NOT call Scheduler.generateAllSchedules().
def test_validator_failure_prevents_schedule_generation(make_program_entry):
    # Arrange — a mock validator that fails, and a mock scheduler whose
    # generateAllSchedules() we will assert was never called.
    failing_validator = MagicMock()
    failing_validator.validate.return_value = False

    mock_scheduler = MagicMock()
    mock_scheduler.generateAllSchedules = MagicMock()

    # We import the orchestration entry point lazily so this test can
    # still load even if the module is renamed during development.
    from src.main import run_pipeline  # type: ignore
    selected = ["83101"]
    # Act — run the pipeline with the failing validator injected.
    try:
        run_pipeline(
            courses=[],
            periods=[],
            programs=selected,
            validators=[failing_validator],
            scheduler=mock_scheduler,
            output_writer=MagicMock(),
            output_path="/tmp/should_not_be_used.txt",
        )
    except Exception:
        # An error is acceptable; the critical assertion is below.
        pass
    
    # Assert — the scheduler must NOT have been invoked.
    assert mock_scheduler.generateAllSchedules.call_count == 0


# ===========================================================================
# TC-VAL-009 — MaxProgramsValidator.error_message describes the specific issue
# ===========================================================================
def test_max_programs_error_message_when_too_many():
    v = MaxProgramsValidator()
    selected = ["83101", "83102", "83103", "83104", "83105", "83107"]
    msg = v.error_message(selected)
    assert "6" in msg, "Error message should name the offending count"
    assert "5" in msg, "Error message should name the maximum"


def test_max_programs_error_message_when_empty():
    v = MaxProgramsValidator()
    msg = v.error_message([])
    # The exact wording can vary — just check it's a real explanation, not the default.
    assert "InputValidator" not in msg  # not the abstract base fallback
    assert msg, "error_message must not be empty"


# ===========================================================================
# TC-VAL-010 — ProgramExistenceValidator.error_message names the invalid codes
# ===========================================================================
def test_program_existence_error_message_lists_invalid_codes():
    v = ProgramExistenceValidator(master=["83101", "83102"])
    msg = v.error_message(["83101", "99999", "12345"])
    assert "99999" in msg
    assert "12345" in msg


# ===========================================================================
# TC-VAL-011 — Default error_message in base class is informative
# ===========================================================================
def test_input_validator_default_error_message_names_class():
    # Anonymous subclass that doesn't override error_message
    class DummyValidator(InputValidator):
        def validate(self, selected, master=None) -> bool:
            return False

    msg = DummyValidator().error_message([])
    assert "DummyValidator" in msg, (
        "Default error_message should at least name the validator class"
    )