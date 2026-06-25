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


@dataclass
class ClusterComparisonViewModel:
    """Two representatives shown side by side with differences flagged."""

    left_title: str
    right_title: str
    left_schedule: ScheduleViewModel
    right_schedule: ScheduleViewModel
    # (label, left_value, right_value, differs) rows for the feature comparison.
    feature_rows: List[Tuple[str, str, str, bool]] = field(default_factory=list)
