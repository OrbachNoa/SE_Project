"""
Stores generated schedules in SQLite when there are too many to keep in RAM. 
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
import bisect
import threading
from typing import List

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA

# Store the temporary SQLite database in the operating system temp folder.
_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")

# Maps each criterion id to a safe SQL column name (s_0 .. s_4), following the
# stable order of ALL_CRITERIA.
_SCORE_COLS = {cid: f"s_{i}" for i, cid in enumerate(ALL_CRITERIA)}


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
        # Cache for unpickled batches (batch_id → list[ScheduleDTO]).
        self._batch_cache: dict = {}
        # Cache for batch range metadata (id, first_offset, batch_count).
        # Rebuilt on first access after any write; avoids re-querying on every navigation step.
        self._ranges_cache: list | None = None

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
        """Creates the schedule batch and score tables if they do not already exist."""
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
                "CREATE INDEX IF NOT EXISTS idx_offset ON schedule_batches(first_offset)"
            )
            # Narrow score table: one row per schedule keyed by its
            # global index, one column per sort criterion. Kept deliberately
            # thin (only floats) so it stays small enough for SQLite to ORDER BY
            # almost entirely in memory — this is what makes the global sort fast.
            score_cols = ", ".join(f"{c} REAL" for c in _SCORE_COLS.values())
            self._conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS schedule_scores (
                    gidx INTEGER PRIMARY KEY,
                    {score_cols}
                )
                """
            )
            # No composite score index: a single multi-column index only
            # accelerates the one ORDER BY whose columns match it left-to-right,
            # while taxing every insert. Since the user can pick any of the 120
            # possible criterion orders, the narrow in-RAM table + LIMIT is fast
            # enough on its own, so the index is not worth the write cost.
            self._conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """ Compresses and stores a batch of schedules. 
        This method is useful when the caller still has normal ScheduleDTO objects. 
        In the GUI flow, batches are usually already compressed by child processes. 
        """
        data = zlib.compress(pickle.dumps(batch, protocol=5), level=1)
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int,
                                batch_scores: "List[dict] | None" = None) -> None:
        """Stores a pre-compressed batch. batch_scores (optional): per-schedule
        score dicts written to schedule_scores for global sorting."""
        with self._lock:
            # first_offset marks where this batch starts in the full result list. 
            first_offset = self._total_count
            self._conn.execute(
                "INSERT INTO schedule_batches (first_offset, batch_count, data) "
                "VALUES (?, ?, ?)",
                (first_offset, batch_count, data),
            )
            # Write per-schedule scores into the narrow table so the global ORDER BY can use them.
            if batch_scores:
                placeholders = ", ".join(["?"] * (1 + len(ALL_CRITERIA)))
                rows = [
                    (first_offset + i,
                     *[scores.get(cid, 0.0) for cid in ALL_CRITERIA])
                    for i, scores in enumerate(batch_scores)
                ]
                self._conn.executemany(
                    f"INSERT OR REPLACE INTO schedule_scores VALUES ({placeholders})",
                    rows,
                )
            self._conn.commit()
            self._total_count += batch_count
            self._ranges_cache = None  # new batch added; invalidate range cache

    def clear(self) -> None:
        """
        Deletes all saved schedule results from the previous run. 
        This is called before a new Generate run, so old schedules will not be mixed with the new results.
        """
        with self._lock:
            self._total_count = 0
            self._conn.execute("DELETE FROM schedule_batches")
            self._conn.execute("DELETE FROM schedule_scores")
            self._conn.commit()
            self._batch_cache.clear()
            self._ranges_cache = None

    def _add_to_cache(self, bid: int, batch: list) -> None:
        """Inserts a batch into the FIFO cache, evicting the oldest entry when full."""
        if len(self._batch_cache) >= 100:
            self._batch_cache.pop(next(iter(self._batch_cache)))
        self._batch_cache[bid] = batch

    def _get_ranges(self) -> list:
        """Returns cached (id, first_offset, batch_count) rows, reloading if stale."""
        if self._ranges_cache is None:
            with self._lock:
                self._ranges_cache = self._conn.execute(
                    "SELECT id, first_offset, batch_count "
                    "FROM schedule_batches "
                    "ORDER BY first_offset"
                ).fetchall()
        return self._ranges_cache

    # ── Read ───────────────────────────────────────────────────────────────

    def get_window(self, offset: int, limit: int) -> List[ScheduleDTO]:
        """
        Returns only a small part of the generated schedules. 
        offset is the first schedule index to load. 
        limit is the maximum number of schedules to return.
        """
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, first_offset, batch_count, data
                FROM   schedule_batches
                WHERE  first_offset + batch_count > :start
                  AND  first_offset              < :end
                ORDER BY first_offset
                """,
                {"start": offset, "end": offset + limit},
            ).fetchall()

        result: List[ScheduleDTO] = []
        for bid, first_off, batch_count, raw in rows:
            if bid in self._batch_cache:
                batch = self._batch_cache[bid]
            else:
                batch = pickle.loads(zlib.decompress(raw))
                self._add_to_cache(bid, batch)

            # Convert the global requested range into indexes inside this batch.
            local_start = max(0, offset - first_off)
            local_end   = min(batch_count, offset + limit - first_off)
            result.extend(batch[local_start:local_end])
            if len(result) >= limit:
                break

        return result[:limit]

    # ── Global sort ─────────────────────────────────

    def get_sorted_ids_page(self, priority: List[str], offset: int, limit: int) -> List[int]:
        """
        Returns only a page (limit) of sorted schedule IDs starting from offset.
        This is extremely fast because it only retrieves the specific range needed.
        """
        if not priority:
            return []
        order = ", ".join(f"{_SCORE_COLS[c]} DESC" for c in priority)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT gidx FROM schedule_scores ORDER BY {order} LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [r[0] for r in rows]

    def get_schedules_by_ids(self, gidxs: List[int]) -> List[ScheduleDTO]:
        """Fetches schedules by global index in the order given, using the batch cache."""
        if not gidxs:
            return []

        # Use cached batch ranges to avoid a SQLite round-trip on every call.
        ranges = self._get_ranges()
        if not ranges:
            return []

        offsets = [r[1] for r in ranges]

        # Group requested global indices by their respective batch ID
        batch_to_gidxs = {}
        for g in gidxs:
            idx = bisect.bisect_right(offsets, g) - 1
            if 0 <= idx < len(ranges):
                batch_id, first_off, batch_count = ranges[idx]
                if first_off <= g < first_off + batch_count:
                    batch_to_gidxs.setdefault(batch_id, []).append((g, first_off))

        needed_ids = list(batch_to_gidxs.keys())
        if not needed_ids:
            return []

        # Check which needed_ids are missing from the cache
        missing_ids = [bid for bid in needed_ids if bid not in self._batch_cache]

        # Query batch raw data in chunks of 500 to keep parameter count below SQLite limits.
        batch_id_to_data = {}
        if missing_ids:
            with self._lock:
                for i in range(0, len(missing_ids), 500):
                    chunk = missing_ids[i:i+500]
                    placeholders = ",".join(["?"] * len(chunk))
                    rows = self._conn.execute(
                        f"SELECT id, data FROM schedule_batches WHERE id IN ({placeholders})",
                        chunk
                    ).fetchall()
                    for bid, raw in rows:
                        batch_id_to_data[bid] = raw

        found = {}
        # Fetch from cache first
        for bid in needed_ids:
            if bid in self._batch_cache:
                batch = self._batch_cache[bid]
                for g, first_off in batch_to_gidxs[bid]:
                    found[g] = batch[g - first_off]

        # Decompress, unpickle, and cache missing batches
        for bid, raw in batch_id_to_data.items():
            batch = pickle.loads(zlib.decompress(raw))
            self._add_to_cache(bid, batch)
            for g, first_off in batch_to_gidxs[bid]:
                found[g] = batch[g - first_off]

        # Preserve the requested (sorted) order.
        return [found[g] for g in gidxs if g in found]

    def count(self) -> int:
        """Returns how many schedules were saved in the current run."""
        with self._lock:
            return self._total_count