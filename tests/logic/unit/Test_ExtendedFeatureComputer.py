"""Unit tests for the ExtendedFeatureComputer.

Covers extended feature computations like MAX_REST_DAYS, verifying the negation
logic and display formatting used for scheduling metrics.
"""
from src.application.dto.ScheduleDTO import AssignmentDTO, ScheduleDTO
from src.logic.clustering.Cluster import Cluster
from src.logic.clustering.ClusterSummarizer import ClusterSummarizer
from src.logic.clustering.CriterionDisplay import (
    display_value,
    display_value_to_percentage,
    is_lower_better,
)
from src.logic.clustering.ExtendedFeatureComputer import (
    ExtendedFeatureComputer,
    MAX_REST_DAYS,
)


def _schedule_for_dates(dates):
    return ScheduleDTO(assignments=[
        AssignmentDTO(
            course_id=f"CS{i:03d}",
            course_name=f"Course {i}",
            instructor=f"I{i}",
            date=date,
            semester="A",
            moed="ALEPH",
            program_requirements=[("P", "OBLIGATORY")],
        )
        for i, date in enumerate(dates)
    ])
# ===========================================================================
# TC-EFC-001: Verify MAX_REST_DAYS is stored negated so shorter gaps score higher.
# ===========================================================================
def test_max_rest_days_is_stored_negated_so_shorter_gaps_score_higher():
    # Arrange
    compact = _schedule_for_dates(["2026-01-01", "2026-01-03", "2026-01-05"])
    wide = _schedule_for_dates(["2026-01-01", "2026-01-10", "2026-01-19"])

    # Act
    compact_score = ExtendedFeatureComputer.compute(compact)[MAX_REST_DAYS]
    wide_score = ExtendedFeatureComputer.compute(wide)[MAX_REST_DAYS]

    # Assert
    assert compact_score == -2.0
    assert wide_score == -9.0
    assert compact_score > wide_score
# ===========================================================================
# TC-EFC-002: Verify MAX_REST_DAYS display value is properly formatted.
# ===========================================================================
def test_max_rest_days_display_de_negates_and_keeps_lower_natural_value_better():
    # Arrange
    raw_score = -9.0

    # Act
    shown = display_value(MAX_REST_DAYS, raw_score)

    # Assert
    assert is_lower_better(MAX_REST_DAYS)
    assert shown == "9.0"
    assert display_value_to_percentage(MAX_REST_DAYS, shown) == 55
# ===========================================================================
# TC-EFC-003: Verify ClusterSummarizer correctly translates lower max_rest_days.
# ===========================================================================
def test_cluster_summarizer_treats_lower_max_rest_days_as_the_better_side():
    # Arrange
    compact = Cluster(cluster_id=0, summary={MAX_REST_DAYS: -2.0})
    wide = Cluster(cluster_id=1, summary={MAX_REST_DAYS: -9.0})

    # Act
    ClusterSummarizer().describe_all([compact, wide])

    # Assert
    assert compact.description == "Compact exam spacing overall"
    assert wide.description == "Longer inactive gaps between exams"
