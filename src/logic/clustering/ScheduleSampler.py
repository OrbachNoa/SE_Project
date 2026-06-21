"""Representative sampling so clustering stays fast at scale.

A scheduling run can yield hundreds of thousands of valid schedules. Running
K-means — and especially silhouette-based auto-K — on all of them would stall the
UI. Instead we cluster a uniform random sample (up to ``max_sample`` points) and
scale per-cluster counts back up to the full population. Uniform sampling keeps
the sample representative: the proportion of each family in the sample matches its
proportion in the whole set, in expectation.

This is a distinct, explicit step that sits *before* extraction/clustering in the
pipeline, so it is easy to reason about, test, and swap (e.g. for stratified
sampling later).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np


class ScheduleSampler:
    """Draws a uniform random sample of indices from a population."""

    def __init__(self, max_sample: int = 10_000, seed: int = 42) -> None:
        if max_sample <= 0:
            raise ValueError("max_sample must be positive")
        self._max_sample = max_sample
        self._seed = seed

    @property
    def max_sample(self) -> int:
        return self._max_sample

    def sample_indices(self, population_size: int) -> List[int]:
        """Return a sorted list of sampled indices into a population.

        When the population already fits within ``max_sample`` every index is
        returned (sorted) and no sampling happens.
        """
        if population_size <= 0:
            return []
        if population_size <= self._max_sample:
            return list(range(population_size))

        rng = np.random.default_rng(self._seed)
        idx = rng.choice(population_size, size=self._max_sample, replace=False)
        idx.sort()
        return idx.tolist()

    def sample(self, items: Sequence) -> Tuple[list, List[int]]:
        """Sample from an in-memory sequence.

        Returns ``(sampled_items, original_indices)`` so callers can map a
        clustered position back to the original schedule.
        """
        indices = self.sample_indices(len(items))
        return [items[i] for i in indices], indices
