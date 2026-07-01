"""
Test suite for SolutionBarWidget.

Scope   : The results toolbar is otherwise a passive container of buttons whose
          pagination/counter behaviour lives in (already-tested) presenters, so
          the only genuine logic here is the "jump to solution number" input
          guard. Its QIntValidator constrains the jump target to a real, in-range
          slot — an input-validation edge case that protects the navigation flow.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SBW-001
Fixtures: qapp (tests/conftest.py)
"""
import pytest
from PyQt6.QtGui import QValidator

from src.config import WINDOW_SIZE
from src.gui.features.output.widgets.SolutionBarWidget import SolutionBarWidget

pytestmark = pytest.mark.usefixtures("qapp")


# ===========================================================================
# TC-SBW-001: the solution-number input must only accept an in-range jump
# target. Its validator accepts a number within [1, WINDOW_SIZE], rejects
# non-numeric text outright, and refuses a value above the window size — so a
# user can never jump to a non-existent solution slot.
# ===========================================================================
def test_solution_bar_input_validator_constrains_jump_target():
    # Arrange
    bar = SolutionBarWidget()
    validator = bar.solution_input.validator()

    # Act — QValidator.validate returns (state, text, pos); we read the state.
    in_range = validator.validate("5", 0)[0]
    non_numeric = validator.validate("abc", 0)[0]
    above_max = validator.validate(str(WINDOW_SIZE * 10), 0)[0]

    # Assert
    assert in_range == QValidator.State.Acceptable
    assert non_numeric == QValidator.State.Invalid
    assert above_max != QValidator.State.Acceptable
