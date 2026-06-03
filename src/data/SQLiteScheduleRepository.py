"""SQLiteScheduleRepository — overflow storage for large result sets.

Design choices:
  - One row per *batch* (not per schedule): pickling + compressing 1 000 DTOs
    at once gives ~8:1 compression because course names repeat heavily.
    860 K results → ~860 rows instead of 860 000 rows.
  - zlib level=1 (fast mode): ~3x faster than default and still halves size.
  - WAL journal: allows the main thread to write while something else reads.
  - _total_count is tracked in memory (never need a COUNT(*) query).
  - Thread-safe using threading.Lock() since background thread writes and GUI reads.
"""
from __future__ import annotations

import os
import pickle
import sqlite3
import tempfile
import zlib
import threading
from typing import List

from src.application.dto_viewmodel.schedule_dto import ScheduleDTO

# Default database file path placed in the OS temporary directory
_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")


class SQLiteScheduleRepository:
    """Stores ScheduleDTO objects in batched, compressed SQLite rows."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = db_path
        # In-memory counter to keep tracking total records at O(1) complexity
        self._total_count: int = 0
        # Lock to prevent race conditions between background writer and UI reader thread
        self._lock = threading.Lock()
        self._init_db()

    # ── Init ───────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Initializes the database schema and indices under a thread lock."""
        with self._lock:
            with self._connect() as conn:
                # Store schedules in compressed binary blocks (BLOBs) mapped by offset indices
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schedule_batches (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        first_offset  INTEGER NOT NULL,
                        batch_count   INTEGER NOT NULL,
                        data          BLOB    NOT NULL
                    )
                    """
                )
                # Create index on offset tracking column to accelerate window query seek times
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_offset "
                    "ON schedule_batches(first_offset)"
                )

    def _connect(self) -> sqlite3.Connection:
        """Creates a single connection session forced into WAL journal mode."""
        conn = sqlite3.connect(self._db_path, timeout=10)
        # WAL mode permits concurrent reads by the GUI thread while background writes execute
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """Compress and store an entire batch as a single SQLite row.

        Compressing the full batch together (instead of per-item) exploits
        the repetition of course names/ids across schedules, yielding much
        better compression ratios at the same CPU cost.
        """
        # Execute expensive serialization and compression workflows outside the critical section lock
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)
        batch_count = len(batch)
        
        with self._lock:
            first_offset = self._total_count
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO schedule_batches (first_offset, batch_count, data) "
                    "VALUES (?, ?, ?)",
                    (first_offset, batch_count, data),
                )
            # Increment tracking scalar counter within the synchronized state boundaries
            self._total_count += batch_count

    def clear(self) -> None:
        """Delete all data and reclaim disk space (called at the start of each run)."""
        with self._lock:
            self._total_count = 0
            with self._connect() as conn:
                conn.execute("DELETE FROM schedule_batches")
            
            # VACUUM must run outside a transaction — open a separate autocommit connection.
            conn = self._connect()
            conn.isolation_level = None  # autocommit mode
            conn.execute("VACUUM")
            conn.close()

    # ── Read ───────────────────────────────────────────────────────────────

    def get_window(self, offset: int, limit: int) -> List[ScheduleDTO]:
        """Return `limit` DTOs starting at absolute `offset`.

        Fetches only the batches that overlap [offset, offset+limit),
        unpacks them, and slices to the exact range requested.
        """
        with self._lock:
            with self._connect() as conn:
                # Query index records overlapping with the active navigation bounds window
                rows = conn.execute(
                    """
                    SELECT first_offset, batch_count, data
                    FROM   schedule_batches
                    WHERE  first_offset + batch_count > :start
                      AND  first_offset              < :end
                    ORDER BY first_offset
                    """,
                    {"start": offset, "end": offset + limit},
                ).fetchall()

        result: List[ScheduleDTO] = []
        for first_off, batch_count, raw in rows:
            # Decompress and reconstitute the raw binary block back into a native object list
            batch: List[ScheduleDTO] = pickle.loads(zlib.decompress(raw))
            # Slice and capture only the sub-segments that sit within requested global boundaries
            local_start = max(0, offset - first_off)
            local_end = min(batch_count, offset + limit - first_off)
            result.extend(batch[local_start:local_end])
            # Break parsing pipeline early if collected data satisfies boundary request thresholds
            if len(result) >= limit:
                break

        return result[:limit]

    def count(self) -> int:
        """Return the total number of stored schedules (O(1), from in-memory counter)."""
        with self._lock:
            return self._total_count