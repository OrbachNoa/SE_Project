"""
Test suite for HeuristicRequestParser.

Scope   : Dependency-free keyword parsing of free-text clustering requests into a
          validated ClusterConfig, covering criterion keyword matching (English
          and Hebrew), emphasis-word weight boosting, K extraction from digit and
          spelled-out number patterns, the ValueError-to-default() fallback, and
          both language branches of the interpretation sentence.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-HRP-001, TC-HRP-002, ... TC-HRP-018
Fixtures: none
"""
from __future__ import annotations

import importlib


import json
import os

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "parser_inputs.json")
with open(FIXTURE_PATH, "r", encoding="utf-8") as _f:
    INPUTS = json.load(_f)

from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO, K_MODE_FIXED
from src.logic.clustering.ClusteringScorer import EXTENDED_CRITERIA
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)


# TC-HRP-001
# An English phrase naming a known criterion's keyword ("rest between exams")
# resolves to that single criterion, confirming the keyword table is wired up.
def test_heuristic_request_parser_matches_english_keyword_to_criterion():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_matches_english_keyword_to_criterion"])

    # Assert
    assert config.criteria == (MIN_MANDATORY_GAP,)


# TC-HRP-002
# A different English phrase ("elective conflicts") maps to ELECTIVE_CONFLICTS,
# proving more than one keyword family is reachable, not just a single hit.
def test_heuristic_request_parser_matches_a_second_english_keyword_to_criterion():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_matches_a_second_english_keyword_to_criterion"])

    # Assert
    assert config.criteria == (ELECTIVE_CONFLICTS,)


# TC-HRP-003
# A Hebrew phrase naming the same MIN_MANDATORY_GAP keyword family ("מנוחה בין
# בחינות") resolves to that criterion, proving Hebrew keywords are honored.
def test_heuristic_request_parser_matches_hebrew_keyword_to_criterion():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_matches_hebrew_keyword_to_criterion"])

    # Assert
    assert config.criteria == (MIN_MANDATORY_GAP,)


# TC-HRP-004
# A Hebrew phrase naming the daily-load keyword family ("עומס ביום") resolves
# to MAX_EXAMS_PER_DAY, exercising a second Hebrew keyword family.
def test_heuristic_request_parser_matches_a_second_hebrew_keyword_to_criterion():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_matches_a_second_hebrew_keyword_to_criterion"])

    # Assert
    assert config.criteria == (MAX_EXAMS_PER_DAY,)


# TC-HRP-005
# An English emphasis word ("mostly") in front of a single matched criterion
# boosts that criterion's weight to 3.0, signalling the user's primary intent.
def test_heuristic_request_parser_english_emphasis_boosts_weight_to_three():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_english_emphasis_boosts_weight_to_three"])

    # Assert
    assert config.weights == {AVG_ALL_COURSES_GAP: 3.0}
    assert AVG_ALL_COURSES_GAP in config.criteria


# TC-HRP-006
# A Hebrew emphasis word ("בעיקר") in front of a matched criterion boosts that
# criterion's weight to 3.0, mirroring the English emphasis behavior.
def test_heuristic_request_parser_hebrew_emphasis_boosts_weight_to_three():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_hebrew_emphasis_boosts_weight_to_three"])

    # Assert
    assert config.weights == {MAX_EXAMS_PER_DAY: 3.0}
    assert MAX_EXAMS_PER_DAY in config.criteria


# TC-HRP-007
# Without any emphasis word, no criterion receives a boosted weight, even when
# a criterion keyword is present — emphasis must be explicit.
def test_heuristic_request_parser_without_emphasis_word_applies_no_weight_boost():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_without_emphasis_word_applies_no_weight_boost"])

    # Assert
    assert config.weights == {}


# TC-HRP-008
# The digit pattern "divided into N groups" extracts N as a fixed K, switching
# the config from automatic to fixed K-mode.
def test_heuristic_request_parser_extracts_k_from_divided_into_n_groups():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_extracts_k_from_divided_into_n_groups"])

    # Assert
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 3


# TC-HRP-009
# The digit pattern "N groups" (without "divided into") also extracts N as
# the fixed K, confirming the second half of the regex alternation.
def test_heuristic_request_parser_extracts_k_from_n_groups_suffix():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_extracts_k_from_n_groups_suffix"])

    # Assert
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 6


# TC-HRP-010
# The Hebrew digit-plus-group-word pattern ("3 קבוצות") extracts K the same
# way the English pattern does, confirming the Hebrew group-word branch.
def test_heuristic_request_parser_extracts_k_from_hebrew_digit_pattern():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_extracts_k_from_hebrew_digit_pattern"])

    # Assert
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 3


# TC-HRP-011
# A spelled-out English number word ("six") immediately followed by a group
# word ("groups") within the lookahead window extracts K=6.
def test_heuristic_request_parser_extracts_k_from_spelled_out_english_number():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_extracts_k_from_spelled_out_english_number"])

    # Assert
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 6


# TC-HRP-012
# A spelled-out Hebrew number word ("שלוש") immediately followed by a Hebrew
# group word ("קבוצות") extracts K=3, mirroring the English spelled-out path.
def test_heuristic_request_parser_extracts_k_from_spelled_out_hebrew_number():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_extracts_k_from_spelled_out_hebrew_number"])

    # Assert
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 3


# TC-HRP-013
# A digit not adjacent to any group word (no "groups"/"clusters"/etc. nearby)
# is not interpreted as K, so the config stays in automatic K-mode.
def test_heuristic_request_parser_ignores_a_digit_with_no_group_word():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_ignores_a_digit_with_no_group_word"])

    # Assert
    assert config.k_mode == K_MODE_AUTO
    assert config.k is None


# TC-HRP-014
# When ClusterConfig construction raises ValueError on the parser's own
# kwargs (forced here via monkeypatch, since the keyword table never
# produces invalid kwargs on its own), parse() recovers by falling back to
# ClusterConfig.default() instead of propagating the exception.
def test_heuristic_request_parser_falls_back_to_default_on_value_error(monkeypatch):
    # Arrange
    module = importlib.import_module(
        "src.logic.clustering.llm.HeuristicRequestParser"
    )
    real_default = ClusterConfig.default()

    class ExplodingClusterConfig:
        def __init__(self, *args, **kwargs):
            raise ValueError("forced failure for test")

        @staticmethod
        def default():
            return real_default

    monkeypatch.setattr(module, "ClusterConfig", ExplodingClusterConfig)
    parser = module.HeuristicRequestParser()

    # Act
    config, _ = parser.parse(INPUTS["test_heuristic_request_parser_falls_back_to_default_on_value_error"])

    # Assert
    assert config is real_default
    assert config.k_mode == K_MODE_FIXED
    assert config.k == 4


# TC-HRP-015
# An empty/blank request matches no criteria, no emphasis, and no K, so the
# dataclass default criteria tuple (the five core ScheduleScorer criteria) is
# used and the English "Grouping by ..." sentence lists them with a trailing
# automatic-K clause.
def test_heuristic_request_parser_interpretation_english_branch_for_blank_text():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, interpretation = parser.parse("")

    # Assert
    assert interpretation.startswith("Grouping by")
    assert interpretation.endswith("with an automatic number of families.")
    assert config.k_mode == K_MODE_AUTO


# TC-HRP-016
# The same blank-input scenario in a Hebrew-flagged raw string produces the
# Hebrew sentence branch, proving _is_hebrew correctly switches the language
# of the interpretation text based on the original raw request.
def test_heuristic_request_parser_interpretation_hebrew_branch_for_hebrew_text():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, interpretation = parser.parse(INPUTS["test_heuristic_request_parser_interpretation_hebrew_branch_for_hebrew_text"])

    # Assert
    assert interpretation.startswith("קיבוץ לפי")
    assert interpretation.endswith("עם מספר קבוצות אוטומטי")
    assert config.k_mode == K_MODE_AUTO


# TC-HRP-017
# When the resolved criteria exactly equal the full extended-criteria tuple
# with no weights, the English interpretation collapses to the special
# "overall schedule quality" sentence rather than enumerating every criterion.
def test_heuristic_request_parser_interpretation_all_criteria_english_shortcut():
    # Arrange
    parser = HeuristicRequestParser()
    config = ClusterConfig(criteria=tuple(EXTENDED_CRITERIA), k_mode=K_MODE_AUTO)

    # Act
    interpretation = parser._interpretation(config, None, None, "anything in english")

    # Assert
    assert interpretation == (
        "Grouping by overall schedule quality, with an automatic number of families."
    )


# TC-HRP-018
# The same all-criteria shortcut has a Hebrew counterpart, selected when the
# raw request text contains Hebrew characters.
def test_heuristic_request_parser_interpretation_all_criteria_hebrew_shortcut():
    # Arrange
    parser = HeuristicRequestParser()
    config = ClusterConfig(criteria=tuple(EXTENDED_CRITERIA), k_mode=K_MODE_AUTO)

    # Act
    interpretation = parser._interpretation(config, None, None, "טקסט בעברית")

    # Assert
    assert interpretation == "קיבוץ לפי כל הקריטריונים, עם מספר קבוצות אוטומטי"


# TC-HRP-019
# A request with more than three matched criteria and no emphasis truncates
# the enumerated phrase list to the first three and appends an "and more"
# tail rather than listing every criterion verbatim.
def test_heuristic_request_parser_interpretation_truncates_long_criteria_list():
    # Arrange
    parser = HeuristicRequestParser()

    # Act
    config, interpretation = parser.parse(
        "I want rest between exams, even spacing, fewer elective conflicts, "
        "and a short mandatory span"
    )

    # Assert
    assert len(config.criteria) > 3
    assert interpretation.endswith("and more, with an automatic number of families.")
