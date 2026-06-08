"""SQLiteScheduleRepository — overflow storage for large result sets.

Design choices:
  - One row per *batch* (not per schedule): pickling + compressing 1 000 DTOs
    at once gives ~8:1 compression because course names repeat heavily.
  - zlib level=1 (fast mode): ~3x faster than default and still halves size.
  - WAL journal: allows the main thread to write while something else reads.
  - synchronous=NORMAL: safe with WAL mode, avoids a full fsync on every write.
  - _total_count is tracked in memory (never need a COUNT(*) query).
  - Single persistent connection shared across all operations. Thread safety is
    provided by self._lock — sqlite3's own check_same_thread is disabled because
    our Lock already guarantees mutual exclusion.
  - insert_compressed_batch accepts a pre-compressed blob produced by a child
    process, so the expensive pickle+compress runs in parallel across workers
    instead of serially in the parent writer thread.
"""
from __future__ import annotations

import os
import pickle
import sqlite3
import tempfile
import zlib
import threading
from typing import List

from src.application.dto.ScheduleDTO import ScheduleDTO

# Default database file path placed in the OS temporary directory
_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")


class SQLiteScheduleRepository:
    """Stores ScheduleDTO objects in batched, compressed SQLite rows."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = db_path
        self._total_count: int = 0
        self._lock = threading.Lock()
        # One persistent connection for the lifetime of this repository.
        # All callers go through self._lock, so no two threads ever touch
        # the connection simultaneously — check_same_thread is therefore safe
        # to disable.
        self._conn: sqlite3.Connection = self._open_connection()
        self._init_db()

    # ── Init ───────────────────────────────────────────────────────────────

    def _open_connection(self) -> sqlite3.Connection:
        """Open the single shared connection with WAL mode and fast sync."""
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        # NORMAL skips the full fsync after each write. WAL mode guarantees
        # durability without it, so this is safe and meaningfully faster.
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        """Initialize the schema under the lock on first construction."""
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_batches (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_offset  INTEGER NOT NULL,
                    batch_count   INTEGER NOT NULL,
                    data          BLOB    NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_offset "
                "ON schedule_batches(first_offset)"
            )
            self._conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """Compress and store a batch produced in the current process.

        Used by the CLI path and any caller that still holds live DTO objects.
        Delegates to insert_compressed_batch after compressing locally.
        """
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int) -> None:
        """Store an already-compressed blob produced by a child process.

        The expensive pickle+compress ran inside the worker process (in parallel
        with all other partition workers), so this method only pays for the
        SQLite INSERT under the lock — keeping the writer thread lightweight.
        """
        with self._lock:
            first_offset = self._total_count
            self._conn.execute(
                "INSERT INTO schedule_batches (first_offset, batch_count, data) "
                "VALUES (?, ?, ?)",
                (first_offset, batch_count, data),
            )
            self._conn.commit()
            self._total_count += batch_count

    def clear(self) -> None:
        """Delete all rows and reset the counter (called at the start of each run).

        VACUUM is intentionally omitted: SQLite reuses the freed pages on the
        next run's inserts, so skipping it costs nothing in performance.
        VACUUM was rebuilding the entire database file on every warm start,
        which made warm runs noticeably slower than cold ones.
        """
        with self._lock:
            self._total_count = 0
            self._conn.execute("DELETE FROM schedule_batches")
            self._conn.commit()

    # ── Read ───────────────────────────────────────────────────────────────

    def get_window(self, offset: int, limit: int) -> List[ScheduleDTO]:
        """Return `limit` DTOs starting at absolute `offset`.

        Fetches only the batches that overlap [offset, offset+limit),
        unpacks them, and slices to the exact range requested.
        """
        with self._lock:
            rows = self._conn.execute(
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
            batch: List[ScheduleDTO] = pickle.loads(zlib.decompress(raw))
            local_start = max(0, offset - first_off)
            local_end   = min(batch_count, offset + limit - first_off)
            result.extend(batch[local_start:local_end])
            if len(result) >= limit:
                break

        return result[:limit]

    def count(self) -> int:
        """Return the total number of stored schedules (O(1), from in-memory counter)."""
        with self._lock:
            return self._total_count