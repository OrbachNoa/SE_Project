"""Result models for a clustering run.

These are the plain, picklable objects the GUI / CLI consume. A ``Cluster`` is
one family of similar schedules plus its representative archetype; a
``ClusterResult`` is the whole partition, with enough bookkeeping to scale member
counts back up when a sample was used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class Cluster:
    """One family of similar schedules and its representative archetype."""

    # Stable id of the cluster (0..k-1).
    cluster_id: int

    # Indexes (into the working set) of the schedules that belong to this cluster.
    member_indices: List[int] = field(default_factory=list)

    # Index (into the working set) of the representative schedule — the member
    # closest to the cluster centroid.
    representative_index: int = -1

    # How many schedules the cluster contains within the working set.
    size: int = 0

    # When the population was sampled, an estimate of the cluster's size over the
    # *entire* population (size scaled by population/working_set). Equals ``size``
    # when no sampling happened.
    estimated_population_size: int = 0

    # Average raw feature values of the cluster's members (criterion -> value):
    # the family "profile" the summarizer turns into a sentence.
    summary: Dict[str, float] = field(default_factory=dict)

    # Human-readable one-line description (filled in by ClusterSummarizer).
    description: str = ""

    # The representative schedule's own raw feature values.
    representative_features: Optional[Dict[str, float]] = None


@dataclass(slots=True)
class ClusterResult:
    """The full outcome of clustering the working set into K families."""

    k: int
    clusters: List[Cluster]

    # The criteria that made up the feature vector for this run.
    criteria: List[str]

    # Number of schedules actually fed to the algorithm.
    working_set_size: int

    # Total number of valid schedules in the population.
    population_size: int

    # True when ``working_set_size < population_size`` (a representative sample
    # was used to stay responsive).
    sampled: bool = False

    # The K that was requested before empty-cluster pruning. Set when the caller
    # asked for a specific K; None for auto mode. Differs from k when some
    # requested clusters collapsed to empty after partitioning.
    requested_k: Optional[int] = None

    def get_cluster(self, cluster_id: int) -> Cluster:
        for cluster in self.clusters:
            if cluster.cluster_id == cluster_id:
                return cluster
        raise IndexError(f"cluster {cluster_id} does not exist (have {self.k})")
