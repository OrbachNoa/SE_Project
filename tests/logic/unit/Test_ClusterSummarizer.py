"""
Test suite for ClusterSummarizer.

Scope   : Statistical description logic mapping a cluster's numeric profile into
          human-readable text via Z-scores. Validates that outliers are picked
          up, fallback messages apply to balanced sets, and exceptions during
          the summary process don't crash the UI.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-SUM-001..004
"""
from unittest.mock import patch

from src.logic.clustering.Cluster import Cluster
from src.logic.clustering.ClusterSummarizer import ClusterSummarizer


def _make_cluster(summary_dict):
    c = Cluster([], set())
    c.summary = summary_dict
    return c


# ===========================================================================
# TC-SUM-001: describe_all extracts the strongest standout criteria (z >= 0.6)
# and formats them into a semi-colon separated sentence.
# ===========================================================================
@patch("src.logic.clustering.CriterionDisplay.standout_phrases")
def test_cluster_summarizer_picks_highest_z_scores(mock_phrases):
    # Arrange
    # Mock phrase pairs: (high_phrase, low_phrase)
    mock_phrases.side_effect = lambda crit: {
        "rest_days": ("More rest days", "Fewer rest days"),
        "clashes": ("More clashes", "Fewer clashes"),
        "gaps": ("More gaps", "Fewer gaps"),
    }.get(crit)

    # We make 3 clusters so we can have a mean and std-dev.
    # C1 is wildly high on rest_days, very low on clashes.
    c1 = _make_cluster({"rest_days": 10.0, "clashes": 0.0, "gaps": 5.0})
    c2 = _make_cluster({"rest_days": 2.0,  "clashes": 8.0, "gaps": 5.0})
    c3 = _make_cluster({"rest_days": 2.0,  "clashes": 8.0, "gaps": 5.0})

    summarizer = ClusterSummarizer()

    # Act
    summarizer.describe_all([c1, c2, c3])

    # Assert
    # c1 rest_days mean = 4.66, c1 is 10 -> high z-score.
    # c1 clashes mean = 5.33, c1 is 0 -> low z-score.
    assert "More rest days" in c1.description
    assert "Fewer clashes" in c1.description


# ===========================================================================
# TC-SUM-002: describe_all returns the fallback text if no trait breaks the
# standout threshold (e.g. perfectly balanced clusters).
# ===========================================================================
def test_cluster_summarizer_fallback_for_balanced_clusters():
    # Arrange — All clusters are identical, so std deviation is 0.
    c1 = _make_cluster({"rest_days": 5.0})
    c2 = _make_cluster({"rest_days": 5.0})

    summarizer = ClusterSummarizer()

    # Act
    summarizer.describe_all([c1, c2])

    # Assert — 0 std means z-score is 0, so no standouts.
    assert c1.description == "A balanced group with no strongly distinctive trait"
    assert c2.description == "A balanced group with no strongly distinctive trait"


# ===========================================================================
# TC-SUM-003: describe_all degrades gracefully and assigns an empty string
# if an internal calculation completely crashes.
# ===========================================================================
@patch.object(ClusterSummarizer, "_population_stats")
def test_cluster_summarizer_swallows_exceptions(mock_stats):
    # Arrange
    mock_stats.side_effect = Exception("Math Error")
    c1 = _make_cluster({"rest_days": 5.0})

    summarizer = ClusterSummarizer()

    # Act
    summarizer.describe_all([c1])

    # Assert — The exception is caught and description is safely blanked.
    assert c1.description == ""


# ===========================================================================
# TC-SUM-004: empty input lists are handled safely.
# ===========================================================================
def test_cluster_summarizer_empty_list():
    # Arrange
    summarizer = ClusterSummarizer()

    # Act
    result = summarizer.describe_all([])

    # Assert — an empty partition is a safe no-op: the early-return guard
    # returns None and raises nothing.
    assert result is None
