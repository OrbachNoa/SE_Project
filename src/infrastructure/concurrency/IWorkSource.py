"""Abstraction the process runner pulls its work from.

The runner depends on this interface, not on a concrete queue, so the static
strategy of yesterday and the dynamic work-stealing strategy can coexist as
different implementations (OCP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.logic.parallel.WorkUnit import WorkUnit


class IWorkSource(ABC):
    """Hands out work units one at a time until the work is exhausted."""

    @abstractmethod
    def get_next(self) -> Optional[WorkUnit]:
        """Returns the next WorkUnit, or None when this worker has no more work."""
        raise NotImplementedError
