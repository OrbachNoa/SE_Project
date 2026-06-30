"""
Test suite for SortCriteria.

Scope   : Verifies label_for() behavior for resolving criterion labels.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SRT-001, TC-SRT-002
Fixtures: none
"""
from src.logic.comparators.SortCriteria import label_for
from src.logic.comparators.ScheduleScorer import ELECTIVE_CONFLICTS


# TC-SRT-001
# label_for must return the human-readable text for a known criterion ID.
def test_label_for_returns_readable_text_for_known_criterion():
    # Act
    result = label_for(ELECTIVE_CONFLICTS)

    # Assert
    assert result == "Fewer elective-exam conflicts"


# TC-SRT-002
# label_for must fall back to returning the raw ID string if the criterion
# ID is unknown (not in the dictionary), ensuring the UI doesn't crash or
# display nothing.
def test_label_for_falls_back_to_raw_id_for_unknown_criterion():
    # Act
    result = label_for("some_unknown_criterion")

    # Assert
    assert result == "some_unknown_criterion"
