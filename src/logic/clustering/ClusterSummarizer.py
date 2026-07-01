"""Turns a cluster's numeric profile into a short human-readable description.

This is the default, dependency-free summary: pure statistical rules, no LLM. For
each cluster we look at how its average score on each criterion compares to the
*other* clusters, pick the one or two criteria where it stands out most, and turn
those into a plain sentence like "More spacing between mandatory exams; fewer
exams on the busiest day".

Because the contract is just ``Cluster -> str``, the future LLM summary can drop
straight in behind the same method without changing the cluster view. Failures
are swallowed (a cluster keeps an empty description) so a bad summary can never
blank the screen.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from src.logic.clustering.Cluster import Cluster
from src.logic.clustering import CriterionDisplay

# Z-score magnitude under which a cluster is "average" on a criterion.
_STANDOUT_THRESHOLD = 0.6


class ClusterSummarizer:
    """Describes each cluster relative to the rest of the partition."""

    def describe_all(self, clusters: List[Cluster]) -> None:
        """Fill in ``cluster.description`` for every cluster (in place)."""
        if not clusters:
            return
        try:
            stats = self._population_stats(clusters)
            for cluster in clusters:
                cluster.description = self._describe(cluster, stats)
        except Exception:
            # Never let summary failure break the cluster view.
            for cluster in clusters:
                if not cluster.description:
                    cluster.description = ""

    # ── internals ──────────────────────────────────────────────────────────────

    def _population_stats(self, clusters: List[Cluster]) -> Dict[str, tuple]:
        """Per-criterion (mean, std) across the cluster centroids' profiles."""
        criteria = set()
        for c in clusters:
            criteria.update(c.summary.keys())

        stats: Dict[str, tuple] = {}
        for crit in criteria:
            values = np.array([c.summary.get(crit, 0.0) for c in clusters], dtype=float)
            stats[crit] = (float(values.mean()), float(values.std()))
        return stats

    def _describe(self, cluster: Cluster, stats: Dict[str, tuple]) -> str:
        if not cluster.summary:
            return ""

        # Score every criterion by how far this cluster deviates from the mean.
        standouts = []
        for crit, value in cluster.summary.items():
            mean, std = stats.get(crit, (0.0, 0.0))
            if std == 0:
                continue
            z = (value - mean) / std
            phrase_pair = CriterionDisplay.standout_phrases(crit)
            if abs(z) >= _STANDOUT_THRESHOLD and phrase_pair is not None:
                high_phrase, low_phrase = phrase_pair
                standouts.append((abs(z), high_phrase if z > 0 else low_phrase))

        if not standouts:
            return "A balanced group with no strongly distinctive trait"

        # Take the two most distinctive traits, strongest first.
        standouts.sort(key=lambda t: t[0], reverse=True)
        chosen = [phrase for _, phrase in standouts[:2]]

        sentence = "; ".join(chosen)
        return sentence[0].upper() + sentence[1:]
