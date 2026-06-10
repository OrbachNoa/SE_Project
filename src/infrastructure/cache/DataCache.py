"""Serializable snapshot of the parsed input data saved on disk.
DataCache is used only for persistence. 
It stores the parsed courses and exam periods in a simple format that can be 
saved and loaded later, without parsing the original input files again.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict
from datetime import datetime, timezone

# Version of the cache file format. 
# If the cache structure changes, older cache files can be rejected instead of being loaded incorrectly.
CURRENT_SCHEMA_VERSION: int = 1

class CourseDict(TypedDict, total=False):
    """Serialized form of a Course object inside the cache."""
    courseId: str
    name: str
    instructor: str
    evaluation: str
    programEntries: list[dict[str, Any]]


class PeriodDict(TypedDict, total=False):
    """Serialized form of an ExamPeriod object inside the cache."""
    semester: str
    moed: str
    startDate: str
    endDate: str
    excludedDates: list[str]

@dataclass
class DataCache:
    """Plain data container for the saved input-data snapshot.
    """

    # Parsed courses saved in a simple dictionary format.
    courses: list[CourseDict] = field(default_factory=list)
    
    # Parsed exam periods saved in a simple dictionary format.
    periods: list[PeriodDict] = field(default_factory=list)

    # Hashes of the original input files.
    # They are used to check if the files changed since the cache was created.
    source_hashes: dict[str, str] = field(default_factory=dict)

    # Time when this cache snapshot was created.
    saved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Cache format version, used to detect old cache files in future versions.
    schema_version: int = CURRENT_SCHEMA_VERSION