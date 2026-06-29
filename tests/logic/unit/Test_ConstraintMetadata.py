"""
Test suite for ConstraintMetadata.

Scope   : Verifies the ConstraintMeta dataclass construction and the exact
          field values (field_name, min_k, max_k, default_k, unit) declared
          for each optional scheduling rule in the CONSTRAINTS tuple.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CME-001, TC-CME-002, ...
Fixtures: none
"""
from src.logic.checkers.config.ConstraintMetadata import ConstraintMeta, CONSTRAINTS


# ---------------------------------------------------------------------------
# ConstraintMeta construction TC-CME-001..002
# ---------------------------------------------------------------------------

# TC-CME-001
# A ConstraintMeta instance stores every field exactly as given, with no
# silent coercion or reordering of positional/keyword values.
def test_constraint_meta_stores_all_fields_as_given():
    # Arrange
    meta = ConstraintMeta(
        field_name="custom_field",
        label="Custom label",
        description="Custom description",
        unit="units",
        min_k=2,
        max_k=8,
        default_k=4,
    )

    # Act
    values = (
        meta.field_name, meta.label, meta.description,
        meta.unit, meta.min_k, meta.max_k, meta.default_k,
    )

    # Assert
    assert values == ("custom_field", "Custom label", "Custom description", "units", 2, 8, 4)


# TC-CME-002
# ConstraintMeta is frozen, so attribute assignment after construction must
# raise rather than silently mutate shared metadata.
def test_constraint_meta_is_immutable():
    # Arrange
    meta = ConstraintMeta(
        field_name="x", label="L", description="D", unit="u",
        min_k=1, max_k=10, default_k=5,
    )

    # Act & Assert
    try:
        meta.min_k = 99
        raised = False
    except Exception:
        raised = True
    assert raised is True
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
# CONSTRAINTS tuple — exact field values per rule TC-CME-005..009
# ---------------------------------------------------------------------------

# TC-CME-005
# min_gap_obligatory must declare days 1..30 with a default of 3, matching
# the minimum-gap-between-mandatory-exams rule used throughout the checkers.
def test_constraints_min_gap_obligatory_has_expected_bounds():
    # Arrange
    meta = next(m for m in CONSTRAINTS if m.field_name == "min_gap_obligatory")

    # Act
    bounds = (meta.min_k, meta.max_k, meta.default_k, meta.unit)

    # Assert
    assert bounds == (1, 30, 3, "days")


# TC-CME-006
# min_gap_any must declare days 1..30 with a default of 2.
def test_constraints_min_gap_any_has_expected_bounds():
    # Arrange
    meta = next(m for m in CONSTRAINTS if m.field_name == "min_gap_any")

    # Act
    bounds = (meta.min_k, meta.max_k, meta.default_k, meta.unit)

    # Assert
    assert bounds == (1, 30, 2, "days")


# TC-CME-007
# elective_conflict_cap is the only constraint allowed to have min_k == 0
# (zero same-day elective conflicts is a legal, meaningful setting), with a
# default of 2 and a max of 10 conflicts.
def test_constraints_elective_conflict_cap_allows_zero_minimum():
    # Arrange
    meta = next(m for m in CONSTRAINTS if m.field_name == "elective_conflict_cap")

    # Act
    bounds = (meta.min_k, meta.max_k, meta.default_k, meta.unit)

    # Assert
    assert bounds == (0, 10, 2, "conflicts")


# TC-CME-008
# exam_span must declare days 1..60 with a default of 7.
def test_constraints_exam_span_has_expected_bounds():
    # Arrange
    meta = next(m for m in CONSTRAINTS if m.field_name == "exam_span")

    # Act
    bounds = (meta.min_k, meta.max_k, meta.default_k, meta.unit)

    # Assert
    assert bounds == (1, 60, 7, "days")


# TC-CME-009
# max_exams_per_day must declare 1..10 exams/day with a default of 3.
def test_constraints_max_exams_per_day_has_expected_bounds():
    # Arrange
    meta = next(m for m in CONSTRAINTS if m.field_name == "max_exams_per_day")

    # Act
    bounds = (meta.min_k, meta.max_k, meta.default_k, meta.unit)

    # Assert
    assert bounds == (1, 10, 3, "exams / day")


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
