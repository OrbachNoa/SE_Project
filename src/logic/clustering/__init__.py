"""Clustering engine: group a large set of valid schedules into a few families.

On entering the cluster screen the app turns hundreds of thousands of valid
schedules into a handful of representative "families" (archetypes) with no
configuration from the user. The engine is split into independent, swappable
Strategy components:

    sample -> extract features -> normalize -> choose K -> cluster -> summarize

so each part can be replaced or extended on its own. It reuses the five sort
scores the engine already computes per schedule as the feature vector (rather than
recomputing anything), which keeps it fast and consistent with how the app ranks.

``ClusteringService`` wires the components together and is driven by a
``ClusterConfig``. Today that config is filled with defaults (all five criteria,
automatic K); the future custom-clustering UI and LLM layer will produce the same
config object from free text, plugging in with no engine change.
"""
from src.logic.clustering.ClusterConfig import ClusterConfig
from src.logic.clustering.Cluster import Cluster, ClusterResult
from src.logic.clustering.ClusteringService import ClusteringService
from src.logic.clustering.ScheduleSampler import ScheduleSampler

__all__ = [
    "ClusterConfig",
    "Cluster",
    "ClusterResult",
    "ClusteringService",
    "ScheduleSampler",
]
