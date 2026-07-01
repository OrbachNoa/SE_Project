"""
Test suite for ConstraintMetadata.

Scope   : Verifies ConstraintMeta immutability, the shape of the CONSTRAINTS
          tuple (arity, field names, element type), and the cross-field
          invariants every declared rule must satisfy (min_k < max_k and
          default_k within [min_k, max_k]).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CME-002, TC-CME-003, TC-CME-004, TC-CME-010
Fixtures: none
"""
from dataclasses import FrozenInstanceError

import pytest

from src.logic.checkers.config.ConstraintMetadata import ConstraintMeta, CONSTRAINTS


# ---------------------------------------------------------------------------
# ConstraintMeta immutability TC-CME-002
# ---------------------------------------------------------------------------

# TC-CME-002
# ConstraintMeta is frozen, so attribute assignment after construction must
# raise FrozenInstanceError rather than silently mutate shared metadata.
def test_constraint_meta_is_immutable():
    # Arrange
    meta = ConstraintMeta(
        field_name="x", label="L", description="D", unit="u",
        min_k=1, max_k=10, default_k=5,
    )

    # Act & Assert
    with pytest.raises(FrozenInstanceError):
        meta.min_k = 99
    assert meta.min_k == 1


# ---------------------------------------------------------------------------
# CONSTRAINTS tuple — shape TC-CME-003..004
# ---------------------------------------------------------------------------

# TC-CME-003
# The CONSTRAINTS tuple must declare exactly five rules, matching the five
# optional scheduling constraints the rest of the system builds checkers for.
def test_constraints_tuple_has_exactly_five_entries():
    # Act
    field_names = [meta.field_name for meta in CONSTRAINTS]

    # Assert
    assert len(CONSTRAINTS) == 5
    assert field_names == [
        "min_gap_obligatory",
        "min_gap_any",
        "elective_conflict_cap",
        "exam_span",
        "max_exams_per_day",
    ]


# TC-CME-004
# Every entry in CONSTRAINTS must be a ConstraintMeta instance, so downstream
# code (ConstraintsConfig.validate, CheckerFactory) can rely on a uniform shape.
def test_constraints_tuple_entries_are_all_constraint_meta():
    # Act
    types = [type(meta) for meta in CONSTRAINTS]

    # Assert
    assert all(t is ConstraintMeta for t in types)


# ---------------------------------------------------------------------------
# Cross-field invariants TC-CME-010
# ---------------------------------------------------------------------------

# TC-CME-010
# For every declared constraint, min_k must be strictly less than max_k, and
# default_k must fall within [min_k, max_k] inclusive -- an out-of-range
# default would silently violate ConstraintsConfig.validate() for any caller
# that uses the declared default unmodified.
def test_constraints_default_k_is_within_min_max_for_every_rule():
    # Act
    violations = [
        meta.field_name
        for meta in CONSTRAINTS
        if not (meta.min_k < meta.max_k and meta.min_k <= meta.default_k <= meta.max_k)
    ]

    # Assert
    assert violations == []
