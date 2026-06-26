"""View models for the cluster screens.

Flat, primitive-only display objects produced by ``ViewModelMapper`` and consumed
by the cluster overview, detail, and comparison screens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel


@dataclass
class ClusterCardViewModel:
    """One card on the cluster overview screen."""

    # 0-based cluster id.
    cluster_id: int
    # Display title, e.g. "Family 1".
    title: str
    # Number of schedules in the cluster (within the working set).
    size: int
    # Estimated size over the full population when the set was sampled.
    estimated_population_size: int
    # True when sizes are estimates from a sample.
    sampled: bool
    # One-line human description of the family's character.
    description: str = ""
    # Raw criterion ids for this clustering run (drives the display loop).
    criteria: tuple = field(default_factory=tuple)
    # Raw average feature values: criterion_id -> float.
    summary: Dict[str, float] = field(default_factory=dict)
    # The top 5 sorted metrics by goodness score for display on the card.
    best_summary: List[Tuple[str, str, str]] = field(default_factory=list)
    # The key of the defining criterion (the one that stands out the most)
    defining_criterion: str = ""
    # Formatted range bounds: criterion_key -> (min_val_str, max_val_str)
    min_max: Dict[str, Tuple[str, str]] = field(default_factory=dict)


@dataclass
class ClusterComparisonViewModel:
    """Two representatives shown side by side with differences flagged."""

    left_title: str
    right_title: str
    left_schedule: ScheduleViewModel
    right_schedule: ScheduleViewModel
    # (criterion_id, label, left_value, right_value, differs) rows for the feature comparison.
    feature_rows: List[Tuple[str, str, str, str, bool]] = field(default_factory=list)
    # Composite labels mapping cluster performance into human-readable ratings — left family.
    left_student_comfort: str = ""
    left_admin_load: str = ""
    left_faculty_impact: str = ""
    left_schedule_spread: str = ""
    # Composite labels for the right family.
    right_student_comfort: str = ""
    right_admin_load: str = ""
    right_faculty_impact: str = ""
    right_schedule_spread: str = ""
    # Raw feature dicts for differential indicators: criterion_id -> display string
    left_features: dict = field(default_factory=dict)
    right_features: dict = field(default_factory=dict)

