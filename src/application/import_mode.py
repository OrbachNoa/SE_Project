"""Import modes for loading data into application state."""
from __future__ import annotations

from enum import Enum


class ImportMode(Enum):
    """Whether an import replaces existing data or merges on top of it."""

    REPLACE = "REPLACE"
    UPDATE = "UPDATE"