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

================================================================================
DEVELOPER NOTE: WHY THIS FILE IS REQUIRED AND MUST REMAIN FREE OF IMPORTS
================================================================================
1. Package Marker:
   This __init__.py file must exist to explicitly designate "src.logic.clustering"
   as a standard Python package. Deleting it would turn this into a PEP 420
   namespace package, which degrades import performance (filesystem search path traversal),
   breaks module path resolution, and causes packaging tools (setuptools) and static 
   analyzers (mypy, Pyright, IDE autocompletion) to fail to discover the modules.

2. Performance (Strictly No Eager Imports):
   Do NOT import any classes/modules inside this file (keep it free of runtime code).
   This package pulls in heavy dependencies like scikit-learn and scipy (via
   ClusteringService -> AutoKSelector), which cost ~1.9s to import.
   
   Because scheduler worker processes import other submodules under this directory 
   (e.g., QueueScheduleObserver -> ExtendedFeatureComputer), adding eager imports 
   here would force every worker process to pay that 1.9s import penalty on every 
   generation run. Always import submodules directly at the consumer level, e.g.:
   
       from src.logic.clustering.ClusteringService import ClusteringService
"""
