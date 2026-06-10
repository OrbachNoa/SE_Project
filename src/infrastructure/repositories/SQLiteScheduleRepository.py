"""Stores generated schedules in SQLite when there are too many to keep in RAM. 
This repository is used for generated schedule results, not for input files. 
Schedules are stored in compressed batches, so the GUI can browse large result 
sets without loading everything into memory at once.
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

# Store the temporary SQLite database in the operating system temp folder.
_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")


class SQLiteScheduleRepository:
    """Stores ScheduleDTO objects in batched, compressed SQLite rows."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = db_path
        # Total number of schedules saved in this run. 
        # This avoids running COUNT(*) on the database every time the GUI asks for the total.
        self._total_count: int = 0
        # Protects the SQLite connection because this repository may be accessed from different threads.
        self._lock = threading.Lock()
        # One SQLite connection is reused for all operations. 
        # check_same_thread is disabled because access is protected by self._lock.
        self._conn: sqlite3.Connection = self._open_connection()
        self._init_db()

    # ── Init ───────────────────────────────────────────────────────────────

    def _open_connection(self) -> sqlite3.Connection:
        """Opens the SQLite connection and configures it for faster batch writes."""
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        # WAL mode allows reading and writing to work better together.
        conn.execute("PRAGMA journal_mode=WAL")
        # NORMAL is faster than FULL and is acceptable here with WAL mode.
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        """Creates the schedule batch table if it does not already exist."""
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
            # Index used by get_window to find the relevant batches quickly.
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_offset "
                "ON schedule_batches(first_offset)"
            )
            self._conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """ Compresses and stores a batch of schedules. 
        This method is useful when the caller still has normal ScheduleDTO objects. 
        In the GUI flow, batches are usually already compressed by child processes. 
        """
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int) -> None:
        """
        Stores a schedule batch that was already compressed by a scheduler process. 
        This keeps this repository fast, because it only writes 
        the blob to SQLite instead of doing the expensive pickle and compression work here.
        """
        with self._lock:
            # first_offset marks where this batch starts in the full result list. 
            # Example: if 2000 schedules were already saved, this batch starts at 2000.
            first_offset = self._total_count
            self._conn.execute(
                "INSERT INTO schedule_batches (first_offset, batch_count, data) "
                "VALUES (?, ?, ?)",
                (first_offset, batch_count, data),
            )
            self._conn.commit()
            # Update the in-memory total after the batch was saved.
            self._total_count += batch_count

    def clear(self) -> None:
        """
        Deletes all saved schedule results from the previous run. 
        This is called before a new Generate run, so old schedules will not be mixed with the new results.
        """
        with self._lock:
            self._total_count = 0
            self._conn.execute("DELETE FROM schedule_batches")
            self._conn.commit()

    # ── Read ───────────────────────────────────────────────────────────────

    def get_window(self, offset: int, limit: int) -> List[ScheduleDTO]:
        """
        Returns only a small part of the generated schedules. 
        offset is the first schedule index to load. 
        limit is the maximum number of schedules to return.
        This is used by the GUI so it can show one page/window 
        of results without loading all generated schedules into memory.
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
            # Decompress only the batches that overlap the requested window.
            batch: List[ScheduleDTO] = pickle.loads(zlib.decompress(raw))
            # Convert the global requested range into indexes inside this batch.
            local_start = max(0, offset - first_off)
            local_end   = min(batch_count, offset + limit - first_off)
            result.extend(batch[local_start:local_end])
            if len(result) >= limit:
                break

        return result[:limit]

    def count(self) -> int:
        """Returns how many schedules were saved in the current run.."""
        with self._lock:
            return self._total_count