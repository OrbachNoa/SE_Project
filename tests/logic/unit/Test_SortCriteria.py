"""
Test suite for SortCriteria.

Scope   : Verifies CRITERION_LABELS is built from SORT_CRITERION_LABELS and
          that label_for() resolves known criterion ids while falling back
          to the raw id for unknown ones.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SRT-001, TC-SRT-002, ...
Fixtures: none
"""
from src.logic.comparators.SortCriteria import ALL_CRITERIA, CRITERION_LABELS, label_for
from src.logic.clustering.CriterionMetadata import SORT_CRITERION_LABELS
from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP,
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
)


# ---------------------------------------------------------------------------
# CRITERION_LABELS construction TC-SRT-001..003
# ---------------------------------------------------------------------------

# TC-SRT-001
# CRITERION_LABELS must be a plain dict copy of SORT_CRITERION_LABELS, not a
# live reference -- mutating one must not affect the other module's table.
def test_criterion_labels_is_a_copy_not_the_same_object():
    # Act & Assert
    assert CRITERION_LABELS == SORT_CRITERION_LABELS
    assert CRITERION_LABELS is not SORT_CRITERION_LABELS


# TC-SRT-002
# Every criterion id in ALL_CRITERIA must have a corresponding entry in
# CRITERION_LABELS, so the sort-config UI never has to fall back to a raw id
# for a criterion the scorer actually produces.
def test_criterion_labels_covers_every_all_criteria_entry():
    # Act
    missing = [c for c in ALL_CRITERIA if c not in CRITERION_LABELS]

    # Assert
    assert missing == []


# TC-SRT-003
# CRITERION_LABELS must contain exactly the five scoring criteria defined by
# ScheduleScorer, with the expected human-readable text for each.
def test_criterion_labels_has_expected_entries_for_all_five_criteria():
    # Act
    labels = {
        MIN_MANDATORY_GAP: CRITERION_LABELS.get(MIN_MANDATORY_GAP),
        AVG_ALL_COURSES_GAP: CRITERION_LABELS.get(AVG_ALL_COURSES_GAP),
        ELECTIVE_CONFLICTS: CRITERION_LABELS.get(ELECTIVE_CONFLICTS),
        MANDATORY_SPAN: CRITERION_LABELS.get(MANDATORY_SPAN),
        MAX_EXAMS_PER_DAY: CRITERION_LABELS.get(MAX_EXAMS_PER_DAY),
    }

    # Assert
    assert labels == {
        MIN_MANDATORY_GAP: "Min gap between mandatory exams (larger first)",
        AVG_ALL_COURSES_GAP: "Avg gap between all exams (larger first)",
        ELECTIVE_CONFLICTS: "Fewer elective-exam conflicts",
        MANDATORY_SPAN: "Span of mandatory exams (larger first)",
        MAX_EXAMS_PER_DAY: "Fewer exams on the busiest day",
    }


# ---------------------------------------------------------------------------
# label_for() TC-SRT-004..005
# ---------------------------------------------------------------------------

# TC-SRT-004
# label_for() must return the human-readable label for a known criterion id.
def test_label_for_returns_human_readable_label_for_known_criterion():
    # Act
    result = label_for(MIN_MANDATORY_GAP)

    # Assert
    assert result == "Min gap between mandatory exams (larger first)"


# TC-SRT-005
# label_for() must fall back to the raw id itself when the criterion is not
# present in CRITERION_LABELS, instead of raising a KeyError.
def test_label_for_falls_back_to_raw_id_for_unknown_criterion():
    # Arrange
    unknown_id = "TOTALLY_UNKNOWN_CRITERION"

    # Act
    result = label_for(unknown_id)

    # Assert
    assert result == unknown_id
