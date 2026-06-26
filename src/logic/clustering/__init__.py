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

Deliberately no eager imports here: this package pulls in scikit-learn/scipy
(via ClusteringService -> AutoKSelector), which costs ~1.9s to import. Every
scheduler worker process imports QueueScheduleObserver -> ExtendedFeatureComputer,
a submodule of this package that has nothing to do with clustering, and previously
paid that cost on every "Generate" click for every worker process. Import the
submodules you need directly, e.g. ``from src.logic.clustering.ClusteringService
import ClusteringService``.
"""
