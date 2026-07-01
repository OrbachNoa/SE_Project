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
from src.logic.clustering.llm.ClusterTranslationError import ClusterTranslationError
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.comparators.ScheduleScorer import MIN_MANDATORY_GAP

import pytest
from unittest.mock import MagicMock


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


# ===========================================================================
# TC-CRT-003: a configured LLM that fails must raise ClusterTranslationError
# rather than silently degrading to the keyword parser -- a transient/real
# failure should surface as an error the caller can report, not a result the
# user never asked for.
# ===========================================================================
def test_translate_configured_llm_failure_raises_and_does_not_fall_back():
    # Arrange
    llm = MagicMock(spec=ILLMClient)
    llm.is_available.return_value = True
    llm.complete.side_effect = RuntimeError("connection refused")
    translator = ClusterRequestTranslator(llm)

    # Act / Assert
    with pytest.raises(ClusterTranslationError), pytest.warns(RuntimeWarning, match="LLM clustering request failed"):
        translator.translate("group by rest days")
    llm.complete.assert_called_once()


# ===========================================================================
# TC-CRT-004: when no LLM is configured (is_available() is False), translate
# must fall through to the keyword parser instead of attempting a call.
# ===========================================================================
def test_translate_unavailable_llm_falls_back_to_heuristic():
    # Arrange
    llm = MagicMock(spec=ILLMClient)
    llm.is_available.return_value = False
    translator = ClusterRequestTranslator(llm)

    # Act
    result = translator.translate("group by rest days")

    # Assert
    assert result.source == "heuristic"
    llm.complete.assert_not_called()
