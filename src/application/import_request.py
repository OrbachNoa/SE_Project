"""Request object for a file-import operation."""
from __future__ import annotations

from dataclasses import dataclass

from src.application.import_mode import ImportMode


@dataclass
class ImportRequest:
    """Bundles the inputs the facade needs to import one file."""

    path: str
    file_type: str
    mode: ImportMode