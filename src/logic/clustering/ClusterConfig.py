"""Configuration object that fully describes one clustering run.

The whole point of this object is to be the *single* contract between
"what the user wants" and "what the engine does". Today it is filled in with
responsive defaults over the core score criteria. Tomorrow, the custom-clustering
UI and the LLM translation layer will produce exactly this same object from a
free-text request — so nothing downstream of here needs to change when that step
arrives. That is the seam the future work plugs into.

A ``ClusterConfig`` is intentionally tiny, picklable and validated, so it can be
logged, cached, compared, or sent across a process boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from src.logic.comparators.ScheduleScorer import (
    ALL_CRITERIA,
    ELECTIVE_CONFLICTS,
    MAX_EXAMS_PER_DAY,
    MANDATORY_SPAN,
    AVG_ALL_COURSES_GAP,
    MIN_MANDATORY_GAP,
)
from src.logic.clustering.ExtendedFeatureComputer import (
    ALL_EXTENDED_FEATURES,
)


# How K is decided for a run.
#   "auto"   -> AutoKSelector picks K (silhouette).
#   "fixed"  -> use ``k`` verbatim.
K_MODE_AUTO = "auto"
K_MODE_FIXED = "fixed"


@dataclass(slots=True)
class ClusterConfig:
    """Everything needed to run the clustering pipeline once.

    Defaults reproduce the "open the screen and it just clusters" behaviour
    with a fixed K that keeps first entry responsive. Custom requests can still
    choose automatic K.
    """

    # Which score criteria take part in the feature vector. The default sticks
    # to core scores that are already produced by the scheduler; custom
    # clustering requests may still add extended features, which are computed
    # lazily by the clustering worker.
    criteria: Tuple[str, ...] = tuple(ALL_CRITERIA)

    # Optional per-criterion weight (criterion_id -> weight). Empty means every
    # selected criterion is weighted 1.0. Lets a future request say "group mostly
    # by exam spread" without touching the engine — the WeightedEuclidean metric
    # reads these.
    weights: Dict[str, float] = field(default_factory=dict)

    # Normalization strategy to use: "zscore" or "minmax".
    normalizer: str = "zscore"

    # How the number of clusters is chosen.
    k_mode: str = K_MODE_AUTO

    # The number of clusters when ``k_mode == "fixed"``; ignored for auto.
    k: Optional[int] = None

    # Auto-K search bounds (inclusive). K is searched in [k_min, k_max].
    k_min: int = 3
    k_max: int = 6

    # Upper bound on how many schedules are actually clustered. Above this the
    # pipeline draws a representative sample so the run stays responsive.
    max_sample: int = 500

    # Fixed seed keeps sampling and K-means deterministic, so the same input and
    # config always yield the same families (stable UI).
    seed: int = 42

    def __post_init__(self) -> None:
        self.validate()

    # ── validation ───────────────────────────────────────────────────────────

    def validate(self) -> None:
        """Raise ``ValueError`` if the config could not produce a valid run.

        Centralising validation here means the future `validate_config` step
        for LLM output is just `ClusterConfig(**parsed).validate()`.
        """
        if not self.criteria:
            raise ValueError("at least one criterion must be selected")

        _known = set(ALL_CRITERIA) | set(ALL_EXTENDED_FEATURES)
        unknown = [c for c in self.criteria if c not in _known]
        if unknown:
            raise ValueError(f"unknown criteria: {unknown}")

        if len(set(self.criteria)) != len(self.criteria):
            raise ValueError("criteria must not contain duplicates")

        bad_weights = [c for c in self.weights if c not in _known]
        if bad_weights:
            raise ValueError(f"weights reference unknown criteria: {bad_weights}")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("weights must be non-negative")

        if self.normalizer not in ("zscore", "minmax"):
            raise ValueError(f"invalid normalizer: {self.normalizer!r}")

        if self.k_mode not in (K_MODE_AUTO, K_MODE_FIXED):
            raise ValueError(f"invalid k_mode: {self.k_mode!r}")

        if self.k_mode == K_MODE_FIXED:
            if self.k is None or self.k <= 0:
                raise ValueError("fixed k_mode requires a positive k")

        if self.k_min < 1 or self.k_max < self.k_min:
            raise ValueError("require 1 <= k_min <= k_max")

        if self.max_sample <= 0:
            raise ValueError("max_sample must be positive")

    # ── convenience ──────────────────────────────────────────────────────────

    def weight_vector(self) -> list:
        """Per-selected-criterion weights, in ``criteria`` order (default 1.0)."""
        return [float(self.weights.get(c, 1.0)) for c in self.criteria]

    @staticmethod
    def default() -> "ClusterConfig":
        """The out-of-the-box configuration used on automatic screen entry."""
        return ClusterConfig(
            weights={
                ELECTIVE_CONFLICTS: 1.5,
                MAX_EXAMS_PER_DAY: 1.5,
                MANDATORY_SPAN: 1.0,
                AVG_ALL_COURSES_GAP: 0.8,
                MIN_MANDATORY_GAP: 0.8,
            },
            normalizer="zscore",
            k_mode=K_MODE_FIXED,
            k=4,
        )
