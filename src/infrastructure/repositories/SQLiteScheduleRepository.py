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
from src.application.dto.PackedScheduleCodec import is_packed_blob, row_to_dto, unpack_rows
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
        self._slots = None
        self._init_db()

    def configure_slots(self, slots: list) -> None:
        """Provide slot metadata needed to lazily materialize packed schedules."""
        self._slots = list(slots)

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
            # Narrow score table (Option B): one row per schedule keyed by its
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
            self._conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """ Compresses and stores a batch of schedules. 
        This method is useful when the caller still has normal ScheduleDTO objects. 
        In the GUI flow, batches are usually already compressed by child processes. 
        """
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int,
                                batch_scores: "List[dict] | None" = None) -> None:
        """
        Stores a schedule batch that was already compressed by a scheduler process. 
        This keeps this repository fast, because it only writes 
        the blob to SQLite instead of doing the expensive pickle and compression work here.

        batch_scores (optional, Option B): score dicts for the schedules in this
        batch, in order. When given, they are written to the narrow
        schedule_scores table so the database can sort globally. When omitted,
        behaviour is unchanged (back-compatible).
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
            # Option B: write the per-schedule scores into the narrow table so
            # the global ORDER BY can use them.
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
            # Update the in-memory total after the batch was saved.
            self._total_count += batch_count

    def _scores_for_ids(self, gidxs: List[int]) -> dict:
        if not gidxs:
            return {}
        cols = ", ".join(_SCORE_COLS[cid] for cid in ALL_CRITERIA)
        rows = []
        with self._lock:
            for i in range(0, len(gidxs), 900):
                chunk = gidxs[i:i + 900]
                placeholders = ", ".join(["?"] * len(chunk))
                rows.extend(
                    self._conn.execute(
                        f"SELECT gidx, {cols} FROM schedule_scores WHERE gidx IN ({placeholders})",
                        chunk,
                    ).fetchall()
                )
        return {
            row[0]: {cid: row[i + 1] for i, cid in enumerate(ALL_CRITERIA)}
            for row in rows
        }

    def _decode_batch(self, raw: bytes, first_offset: int, wanted_ids: "set[int] | None" = None) -> dict:
        """Decode one stored batch into {global_index: ScheduleDTO}.

        New runs store compact packed rows; older rows may still be pickled DTO
        batches, so keep the legacy path for compatibility.
        """
        data = zlib.decompress(raw)
        if not is_packed_blob(data):
            batch: List[ScheduleDTO] = pickle.loads(data)
            if wanted_ids is None:
                return {first_offset + i: dto for i, dto in enumerate(batch)}
            return {
                first_offset + i: dto
                for i, dto in enumerate(batch)
                if first_offset + i in wanted_ids
            }

        if self._slots is None:
            raise RuntimeError("SQLiteScheduleRepository.configure_slots() must be called before reading packed schedules")

        _slot_count, rows = unpack_rows(data)
        ids = (
            range(first_offset, first_offset + len(rows))
            if wanted_ids is None
            else sorted(g for g in wanted_ids if first_offset <= g < first_offset + len(rows))
        )
        scores_by_id = self._scores_for_ids(list(ids))

        decoded = {}
        for gidx in ids:
            row = rows[gidx - first_offset]
            decoded[gidx] = row_to_dto(row, self._slots, scores_by_id.get(gidx))
        return decoded

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

        wanted = set(range(offset, offset + limit))
        result_by_id: dict = {}
        for first_off, batch_count, raw in rows:
            overlap = {
                g for g in wanted
                if first_off <= g < first_off + batch_count
            }
            result_by_id.update(self._decode_batch(raw, first_off, overlap))
            if len(result_by_id) >= limit:
                break

        return [result_by_id[g] for g in range(offset, offset + limit) if g in result_by_id]

    # ── Option B: global sort + lazy fetch ─────────────────────────────────

    def get_sorted_ids(self, priority: List[str]) -> List[int]:
        """
        Pass 1 of the global sort: returns the global indexes of ALL schedules,
        ordered by the priority list of criterion ids (each descending, since
        every score is higher-is-better). This reads only the narrow score
        table, so it is fast and returns lightweight integers — the caller holds
        this ordered id list in memory instead of the full schedules.

        Empty priority returns ids in natural (generation) order.
        """
        with self._lock:
            if not priority:
                rows = self._conn.execute(
                    "SELECT gidx FROM schedule_scores ORDER BY gidx"
                ).fetchall()
            else:
                order = ", ".join(f"{_SCORE_COLS[c]} DESC" for c in priority)
                rows = self._conn.execute(
                    f"SELECT gidx FROM schedule_scores ORDER BY {order}"
                ).fetchall()
        return [r[0] for r in rows]

    def get_schedules_by_ids(self, gidxs: List[int]) -> List[ScheduleDTO]:
        """
        Pass 2 of the global sort: fetches the given schedules by global index,
        in the same order as gidxs. Looks up only the specific batches that
        contain the requested ids (via the offset index) and decompresses each
        such batch once — so fetching a screen's worth of schedules touches only
        the few batches they live in, not the whole table.
        """
        if not gidxs:
            return []

        found: dict = {}
        # Cache decompressed batches so several wanted ids in the same batch
        # only cost one decompress.
        batch_cache: dict = {}
        wanted_ids = set(gidxs)
        for g in gidxs:
            if g in found:
                continue
            # Find the one batch whose range covers this global index. The
            # offset index makes this a fast lookup, not a full scan.
            with self._lock:
                row = self._conn.execute(
                    """
                    SELECT id, first_offset, batch_count, data
                    FROM   schedule_batches
                    WHERE  first_offset <= :g
                      AND  first_offset + batch_count > :g
                    LIMIT 1
                    """,
                    {"g": g},
                ).fetchone()
            if row is None:
                continue
            batch_id, first_off, batch_count, raw = row
            if batch_id not in batch_cache:
                batch_wanted = {
                    wanted
                    for wanted in wanted_ids
                    if first_off <= wanted < first_off + batch_count
                }
                batch_cache[batch_id] = self._decode_batch(raw, first_off, batch_wanted)
            found.update(batch_cache[batch_id])

        # Preserve the requested (sorted) order.
        return [found[g] for g in gidxs if g in found]

    def count(self) -> int:
        """Returns how many schedules were saved in the current run.."""
        with self._lock:
            return self._total_count
