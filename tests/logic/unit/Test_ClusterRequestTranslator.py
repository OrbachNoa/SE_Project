"""Unit tests for ClusterRequestTranslator's LLM JSON mapping.

Covers _config_from_llm(): translating the raw JSON returned by the LLM
(topics, optional per-topic thresholds, k_mode, explanation) into a
validated ClusterConfig plus a human-readable interpretation sentence —
including the criteria expanded from a topic, the default weights, the
threshold-driven weight boost, and the auto→fixed k_mode resolution.

Conventions:
- Each test carries a unique TC-CRT-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- No conftest fixture models a raw LLM JSON payload, so each test builds
  its own payload inline with `json.dumps`.
"""
import json

from src.logic.clustering.ExtendedFeatureComputer import (
    B2B_EXAM_INCIDENCE,
    MANDATORY_CONSEC,
)
from src.logic.clustering.llm.ClusterRequestTranslator import ClusterRequestTranslator
from src.logic.comparators.ScheduleScorer import MIN_MANDATORY_GAP


# ===========================================================================
# TC-CRT-001: a "consecutive" topic with k_mode "auto" expands to the topic's
# three criteria with their default weights, and resolves k_mode to a fixed
# k of 2 while echoing the LLM's explanation as the interpretation.
# ===========================================================================
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


# ===========================================================================
# TC-CRT-002: an explicit per-topic threshold on "consecutive" boosts the
# weight of every criterion that topic expands to, above their defaults.
# ===========================================================================
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
