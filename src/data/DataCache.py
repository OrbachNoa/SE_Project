"""Persistence-only DTO for the on-disk data snapshot.

This module defines :class:`DataCache`, the serializable representation of the
parsed application data as it is stored on disk. It exists ONLY at the I/O
boundary and carries no runtime behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict
from datetime import datetime, timezone

# Sets the schema version to 1 because it allows tracking data structure changes for future migrations.
CURRENT_SCHEMA_VERSION: int = 1

# Defines the structure of a serialized course because it provides type safety for the IDE and MyPy.
class CourseDict(TypedDict, total=False):
    courseId: str
    name: str
    instructor: str
    evaluation: str
    programEntries: list[dict[str, Any]]

# Defines the structure of a serialized period because it ensures consistent I/O operations.
class PeriodDict(TypedDict, total=False):
    semester: str
    moed: str
    startDate: str
    endDate: str
    excludedDates: list[str]

@dataclass
class DataCache:
    """A plain data container describing the on-disk snapshot.
    """

    # Holds the serialized courses because the InputDataState needs to reconstruct domain objects from them.
    courses: list[CourseDict] = field(default_factory=list)
    
    # Holds the serialized periods because the system must remember exam windows across sessions.
    periods: list[PeriodDict] = field(default_factory=list)

    # Maps source file paths to their hashes because the FileChangeDetector needs to validate cache freshness.
    source_hashes: dict[str, str] = field(default_factory=dict)

    # Generates an automatic ISO timestamp because it ensures accurate save times without relying on the caller.
    saved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Stores the on-disk format version because it enables smooth migrations for old caches in future versions.
    schema_version: int = CURRENT_SCHEMA_VERSION