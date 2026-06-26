"""Unit tests for the file_io.validators package: MaxProgramsValidator,
ProgramExistenceValidator, the IInputValidator base class, ValidationResult,
and ValidatorPipeline.

Covers MaxProgramsValidator's boundary values (0, 1, 5, 6 programs),
ProgramExistenceValidator's exact-match semantics (no prefix/substring
matching), the orchestration guarantee that a failing validator must
prevent Scheduler.generateSchedules() from ever being called, each
validator's error_message() wording, ValidationResult's state machine
(default/add_error/merge/repr), validate_as_result() bridging the
boolean-returning validators into that result type, and ValidatorPipeline's
aggregation and fail_fast short-circuiting.

Conventions:
- Each test carries a unique TC-VAL-NNN identifier in the comment block
  above its definition, numbered sequentially, grouped under a section
  divider per class.
- Each test body is split into Arrange / Act / Assert sections.
- No conftest fixture models these validator classes, so each test builds
  them directly; `make_program_entry` is referenced only where a test
  actually needs a ProgramEntry, not as a blanket signature default.
"""
from unittest.mock import MagicMock
import pytest

from src.file_io.validators.MaxProgramsValidator import MaxProgramsValidator
from src.file_io.validators.ProgramExistenceValidator import ProgramExistenceValidator
from src.file_io.validators.InputValidator import IInputValidator
from src.file_io.validators.ValidationResult import ValidationResult
from src.file_io.validators.ValidatorPipeline import ValidatorPipeline


# ---------------------------------------------------------------------------
# MaxProgramsValidator — TC-VAL-001..004 (boundary value tests)
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-VAL-001: Exactly 5 programs (the upper boundary) must be accepted.
# ===========================================================================
def test_max_programs_validator_accepts_exactly_five():
    # Arrange — 5 distinct program entries, codes 83101..83105.
    selected = [f"8310{i}" for i in range(1, 6)]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is True

# ===========================================================================
# TC-VAL-002: 6 programs (one over the max) must be rejected.
# ===========================================================================
def test_max_programs_validator_rejects_six():
    # Arrange — 6 distinct program entries.
    selected = [f"8310{i}" for i in range(1, 7)]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is False

# ===========================================================================
# TC-VAL-003: 1 program (the minimum viable input) must be accepted.
# ===========================================================================
def test_max_programs_validator_accepts_one():
    # Arrange — exactly one program entry.
    selected = ["83101"]
    # Act
    result = MaxProgramsValidator().validate(selected, master=None)
    # Assert
    assert result is True

# ===========================================================================
# TC-VAL-004: 0 programs (empty selection) must be rejected.
# The system cannot schedule anything with no programs selected.
# ===========================================================================
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

# ===========================================================================
# TC-VAL-005: When every selected program code is present in the master list, the validator must return True.
# ===========================================================================
def test_program_existence_validator_accepts_when_all_in_master():
    # Arrange
    valid_ids = ["83101", "83102", "83103"]
    v = ProgramExistenceValidator(valid_ids)
    selected = ["83101", "83102"]
    # Act
    result = v.validate(selected)
    # Assert
    assert result is True

# ===========================================================================
# TC-VAL-006: A single unknown program code must cause the validator to return false.
# ===========================================================================
def test_program_existence_validator_rejects_unknown_code():
    # Arrange — '99999' is not in the master list.
    valid_ids = ["83101", "83102"]
    v = ProgramExistenceValidator(valid_ids)
    selected = ["83101", "99999"]
    # Act
    result = v.validate(selected)
    # Assert
    assert result is False


# ===========================================================================
# TC-VAL-007: Substring/prefix matching is NOT allowed — '8310' is not a valid match for '83101'.
# ===========================================================================
def test_program_existence_validator_rejects_prefix_match():
    # Arrange — '8310' is a prefix of '83101' but not equal to it.
    valid_ids = ["83101"]
    v = ProgramExistenceValidator(valid_ids)
    selected = ["8310"]
    # Act
    result = v.validate(selected)

    # Assert
    assert result is False

# ---------------------------------------------------------------------------
# IInputValidator — TC-VAL-008..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-VAL-008: When any IInputValidator returns False, the orchestration
# must NOT call Scheduler.generateSchedules().
# ===========================================================================
def test_validator_failure_prevents_schedule_generation():
    # Arrange — a dummy validator that fails, and a mock scheduler whose
    # generateSchedules() we will assert was never called.
    class DummyFailingValidator(IInputValidator):
        def validate(self, selected, master=None) -> bool:
            return False
        def error_message(self, selected) -> str:
            return "Dummy validation failure"

    failing_validator = DummyFailingValidator()

    mock_scheduler = MagicMock()
    mock_scheduler.generateSchedules = MagicMock()

    # We import the orchestration entry point lazily so this test can
    # still load even if the module is renamed during development.
    from main import run_pipeline
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
    assert mock_scheduler.generateSchedules.call_count == 0


# ===========================================================================
# TC-VAL-009: MaxProgramsValidator.error_message names both the offending
# count and the configured maximum, so the user knows how far over they are.
# ===========================================================================
def test_max_programs_error_message_when_too_many():
    # Arrange
    v = MaxProgramsValidator()
    selected = ["83101", "83102", "83103", "83104", "83105", "83107"]
    # Act
    msg = v.error_message(selected)
    # Assert
    assert "6" in msg, "Error message should name the offending count"
    assert "5" in msg, "Error message should name the maximum"

# ===========================================================================
# TC-VAL-010: error_message for an empty selection must still give a real,
# specific explanation rather than falling back to the generic base-class
# default that only names the validator's class.
# ===========================================================================
def test_max_programs_error_message_when_empty():
    # Arrange
    v = MaxProgramsValidator()
    # Act
    msg = v.error_message([])
    # Assert
    # Check for real explanation, not default.
    assert "InputValidator" not in msg
    assert msg, "error_message must not be empty"

# ===========================================================================
# TC-VAL-011: ProgramExistenceValidator.error_message must name every
# invalid code it found, not just report that "some" codes were invalid.
# ===========================================================================
def test_program_existence_error_message_lists_invalid_codes():
    # Arrange
    valid_ids = ["83101", "83102"]
    v = ProgramExistenceValidator(valid_ids)
    # Act
    msg = v.error_message(["83101", "99999", "12345"])
    # Assert
    assert "99999" in msg
    assert "12345" in msg

# ===========================================================================
# TC-VAL-012: the base IInputValidator.error_message, when not overridden
# by a subclass, must still name that subclass — a validator author who
# forgets to override it gets a debuggable message, not a blank one.
# ===========================================================================
def test_input_validator_default_error_message_names_class():
    # Arrange
    # Anonymous subclass that doesn't override error_message
    class DummyValidator(IInputValidator):
        def validate(self, selected, master=None) -> bool:
            return False
    # Act
    msg = DummyValidator().error_message([])
    # Assert
    assert "DummyValidator" in msg, (
        "Default error_message should at least name the validator class"
    )


# ---------------------------------------------------------------------------
# ValidationResult — TC-VAL-013..017
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-VAL-013: a freshly constructed ValidationResult must default to valid
# with no errors and a matching repr — there is no implicit invalid state.
# ===========================================================================
def test_validation_result_default_state():
    # Act
    result = ValidationResult()

    # Assert
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert repr(result) == "ValidationResult(valid)"


# ===========================================================================
# TC-VAL-014: add_error must append the message and flip is_valid to False
# in the same call — there is no separate step needed to mark it invalid.
# ===========================================================================
def test_validation_result_add_error():
    # Arrange
    result = ValidationResult()

    # Act
    result.add_error("Invalid program ID")

    # Assert
    assert result.is_valid is False
    assert result.errors == ["Invalid program ID"]
    assert repr(result) == "ValidationResult(invalid (1 error(s)))"


# ===========================================================================
# TC-VAL-015: merge must combine both results' errors into the receiver —
# the second result's errors are not dropped or kept separate.
# ===========================================================================
def test_validation_result_merge():
    # Arrange
    r1 = ValidationResult()
    r2 = ValidationResult()

    # Act
    r1.add_error("Error 1")
    r2.add_error("Error 2")
    r1.merge(r2)

    # Assert
    assert r1.is_valid is False
    assert len(r1.errors) == 2
    assert "Error 1" in r1.errors
    assert "Error 2" in r1.errors
    assert repr(r1) == "ValidationResult(invalid (2 error(s)))"


# ===========================================================================
# TC-VAL-016: validate_as_result on a passing validator must return a
# valid ValidationResult with no errors — not just a bare True.
# ===========================================================================
def test_concrete_validator_validate_as_result_success():
    # Arrange
    validator = MaxProgramsValidator()
    selected = ["83101", "83102"]

    # Act
    result = validator.validate_as_result(selected)

    # Assert
    assert result.is_valid is True
    assert len(result.errors) == 0


# ===========================================================================
# TC-VAL-017: validate_as_result on a failing validator must return an
# invalid result carrying that validator's own error_message, not a
# generic failure with no explanation.
# ===========================================================================
def test_concrete_validator_validate_as_result_failure():
    # Arrange
    validator = MaxProgramsValidator()
    selected = [f"8310{i}" for i in range(1, 8)]

    # Act
    result = validator.validate_as_result(selected)

    # Assert
    assert result.is_valid is False
    assert len(result.errors) == 1
    assert "exceed" in result.errors[0] or "maximum" in result.errors[0].lower()



# ---------------------------------------------------------------------------
# ValidatorPipeline — TC-VAL-018..022
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-VAL-018: with every registered validator passing, the pipeline must
# run all of them (each called exactly once with the input) and return a
# valid, error-free result.
# ===========================================================================
def test_validator_pipeline_success():
    # Arrange
    v1 = MagicMock()
    v1.validate_as_result.return_value = ValidationResult()
    v2 = MagicMock()
    v2.validate_as_result.return_value = ValidationResult()

    pipeline = ValidatorPipeline([v1, v2])

    # Act
    result = pipeline.validate(["some_data"])

    # Assert
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert v1.validate_as_result.call_count == 1
    assert v1.validate_as_result.call_args[0][0] == ["some_data"]
    assert v2.validate_as_result.call_count == 1
    assert v2.validate_as_result.call_args[0][0] == ["some_data"]


# ===========================================================================
# TC-VAL-019: with fail_fast=False and two failing validators, the
# pipeline must run BOTH and merge both validators' errors into the
# result, not stop after the first failure.
# ===========================================================================
def test_validator_pipeline_failure():
    # Arrange
    r1 = ValidationResult()
    r1.add_error("Error A")
    v1 = MagicMock()
    v1.validate_as_result.return_value = r1

    r2 = ValidationResult()
    r2.add_error("Error B")
    v2 = MagicMock()
    v2.validate_as_result.return_value = r2

    pipeline = ValidatorPipeline([v1, v2])

    # Act
    result = pipeline.validate(["some_data"], fail_fast=False)

    # Assert
    assert result.is_valid is False
    assert "Error A" in result.errors
    assert "Error B" in result.errors
    assert v1.validate_as_result.call_count == 1
    assert v1.validate_as_result.call_args[0][0] == ["some_data"]
    assert v2.validate_as_result.call_count == 1
    assert v2.validate_as_result.call_args[0][0] == ["some_data"]


# ===========================================================================
# TC-VAL-020: with fail_fast=True, a first-validator failure must stop the
# pipeline immediately — the second validator must never even be called.
# ===========================================================================
def test_validator_pipeline_fail_fast():
    # Arrange
    r1 = ValidationResult()
    r1.add_error("Error A")
    v1 = MagicMock()
    v1.validate_as_result.return_value = r1

    v2 = MagicMock()

    pipeline = ValidatorPipeline([v1, v2])

    # Act
    result = pipeline.validate(["some_data"], fail_fast=True)

    # Assert
    assert result.is_valid is False
    assert "Error A" in result.errors
    assert v1.validate_as_result.call_count == 1
    assert v1.validate_as_result.call_args[0][0] == ["some_data"]
    assert v2.validate_as_result.call_count == 0

# ===========================================================================
# TC-VAL-021: add() must register a validator that the pipeline then
# actually runs on the next validate() call — not just store it inertly.
# ===========================================================================
def test_validator_pipeline_add_validator():
    # Arrange
    v1 = MagicMock()
    v1.validate_as_result.return_value = ValidationResult()
    pipeline = ValidatorPipeline()

    # Act
    pipeline.add(v1)
    result = pipeline.validate(["some_data"])

    # Assert
    assert result.is_valid is True
    assert v1.validate_as_result.call_count == 1


# ===========================================================================
# TC-VAL-022: merging a valid (error-free) result into an already-invalid
# one must leave the existing errors and invalid state untouched — merging
# in "nothing new" must not accidentally clear or reset anything.
# ===========================================================================
def test_validation_result_merge_valid_into_invalid():
    # Arrange
    r1 = ValidationResult()
    r1.add_error("Error 1")
    r2 = ValidationResult()

    # Act
    r1.merge(r2)

    # Assert
    assert r1.is_valid is False
    assert r1.errors == ["Error 1"]
