"""Unit tests for ClusterRequestTranslator's LLM JSON mapping."""
import json

from src.logic.clustering.ExtendedFeatureComputer import (
    B2B_EXAM_INCIDENCE,
    MANDATORY_CONSEC,
)
from src.logic.clustering.llm.ClusterRequestTranslator import ClusterRequestTranslator
from src.logic.comparators.ScheduleScorer import MIN_MANDATORY_GAP


def test_llm_consecutive_topic_builds_valid_config():
    # Arrange
    translator = ClusterRequestTranslator()
    raw = json.dumps({
        "topics": ["consecutive"],
        "k_mode": "auto",
        "explanation": "Grouping by consecutive mandatory exam days",
    })

    # Act
    config, interpretation = translator._config_from_llm(raw)

    # Assert
    assert interpretation == "Grouping by consecutive mandatory exam days"
    assert config.criteria == (
        B2B_EXAM_INCIDENCE,
        MANDATORY_CONSEC,
        MIN_MANDATORY_GAP,
    )
    assert config.weights[MANDATORY_CONSEC] == 3.0
    assert config.weights[B2B_EXAM_INCIDENCE] == 3.0
    assert config.k_mode == "fixed"
    assert config.k == 2


def test_llm_consecutive_threshold_boosts_all_topic_criteria():
    # Arrange
    translator = ClusterRequestTranslator()
    raw = json.dumps({
        "topics": ["consecutive"],
        "thresholds": {"consecutive": 4},
        "k_mode": "auto",
        "explanation": "Grouping by consecutive mandatory exam days",
    })

    # Act
    config, _ = translator._config_from_llm(raw)

    # Assert
    assert config.weights[MANDATORY_CONSEC] == 5.0
    assert config.weights[B2B_EXAM_INCIDENCE] == 5.0
    assert config.weights[MIN_MANDATORY_GAP] == 1.8
