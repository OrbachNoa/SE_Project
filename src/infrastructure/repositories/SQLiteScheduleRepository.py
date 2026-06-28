"""Repository that saves generated schedules in SQLite instead of keeping all of them in RAM.

The scheduler can generate a huge amount of schedules.
So we save them in compressed batches and let the GUI load only the small part
it needs to show right now.
"""
from __future__ import annotations

import os
import pickle
import sqlite3
import tempfile
import zlib
import threading
from typing import List

import numpy as np

from src.application.dto.ScheduleDTO import ScheduleDTO
from src.application.dto.PackedScheduleCodec import is_packed_blob, row_to_dto, unpack_rows
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA


# Default place for the overflow database.
# We use the temp folder because this DB is only for generated results.
_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")

# Map every core score criterion to a short SQLite column name. This never
# depends on clustering, so it stays a module constant.
_SCORE_COLS = {cid: f"s_{i}" for i, cid in enumerate(ALL_CRITERIA)}


class SQLiteScheduleRepository:
    """Stores generated schedules in SQLite so the GUI can browse large result sets."""

    def __init__(self, db_path: str = _DEFAULT_DB, extra_score_criteria: "list[str] | None" = None) -> None:
        # Save the DB path so we can open the same database again.
        self._db_path = db_path

        # Total number of schedules saved in this run.
        self._total_count: int = 0

        # SQLite connection is shared by the worker thread, so we protect it with a lock.
        self._lock = threading.Lock()

        # Separate, cheap lock just for _total_count. count() is polled every
        # 500ms from the GUI thread while the writer thread holds self._lock for
        # the whole insert+commit; sharing one lock made that poll block on disk I/O
        # and stall the GUI. This lock is only ever held for a plain int read/write.
        self._count_lock = threading.Lock()

        # Open the SQLite connection and prepare the tables.
        self._conn: sqlite3.Connection = self._open_connection()

        # Slots are needed later to rebuild packed schedules back into DTOs.
        self._slots = None

        # Sort orders we have already built a covering index for, so each
        # distinct ORDER BY is indexed at most once. Reset on clear().
        self._sort_index_signatures: set[str] = set()

        # Extra score criteria (e.g. clustering features) are supplied by the
        # caller instead of imported here, so the repository never depends on
        # the clustering module directly.
        extra_score_criteria = list(extra_score_criteria or [])
        self._ext_feature_cols = {fid: f"f_{i}" for i, fid in enumerate(extra_score_criteria)}
        self._all_score_criteria = list(ALL_CRITERIA) + extra_score_criteria
        self._all_score_cols = list(_SCORE_COLS.values()) + list(self._ext_feature_cols.values())

        self._init_db()

    def configure_slots(self, slots: list) -> None:
        """Save slot metadata so packed schedules can be decoded later."""
        # We copy the list so later changes outside this class will not surprise us.
        self._slots = list(slots)

    def _open_connection(self) -> sqlite3.Connection:
        """Open the SQLite connection with settings that fit background writing."""
        # check_same_thread=False lets this repository use the connection from another thread.
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)

        # WAL makes reads and writes work better together.
        conn.execute("PRAGMA journal_mode=WAL")

        # NORMAL is faster than FULL, and good enough for temporary generated results.
        conn.execute("PRAGMA synchronous=NORMAL")

        return conn

    def _init_db(self) -> None:
        """Create the tables we need if they do not exist yet."""
        with self._lock:
            # This table stores the actual schedule data.
            # Each row is one compressed batch of schedules.
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schedule_batches ("
                "    id            INTEGER PRIMARY KEY AUTOINCREMENT,"
                "    first_offset  INTEGER NOT NULL,"
                "    batch_count   INTEGER NOT NULL,"
                "    data          BLOB    NOT NULL"
                ")"
            )

            # This index helps us quickly find the batch that contains a specific schedule index.
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_offset "
                "ON schedule_batches(first_offset)"
            )

            # This table stores only the numeric scores.
            # We can sort and cluster schedules without loading the full schedules.
            score_cols = ", ".join(f"{c} REAL" for c in _SCORE_COLS.values())
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS schedule_scores ("
                f"    gidx INTEGER PRIMARY KEY, {score_cols})"
            )
            existing = {
                row[1]
                for row in self._conn.execute("PRAGMA table_info(schedule_scores)").fetchall()
            }
            for col in self._ext_feature_cols.values():
                if col not in existing:
                    self._conn.execute(
                        f"ALTER TABLE schedule_scores ADD COLUMN {col} REAL"
                    )
            self._conn.commit()

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        """Compress and save a normal list of ScheduleDTO objects."""
        # Pickle turns the DTO list into bytes, and zlib makes it smaller.
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)

        # The real insert logic is shared with already-compressed batches.
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int,
                                batch_scores: "List[dict] | None" = None,
                                extended_scores: "List[dict] | None" = None) -> None:
        # first_offset is the global index of the first schedule in this batch.
        # Safe to read without self._count_lock: this method is only ever called
        # from the single background writer thread, so there is no other writer
        # to race against here -- only count() reads concurrently from the GUI thread.
        first_offset = self._total_count

        with self._lock:
            # Save the compressed schedules as one blob.
            self._conn.execute(
                "INSERT INTO schedule_batches (first_offset, batch_count, data) VALUES (?, ?, ?)",
                (first_offset, batch_count, data),
            )

            # If scores were already calculated, save them in the score table too.
            if batch_scores:
                col_list = ", ".join(self._all_score_cols)
                placeholders = ", ".join(["?"] * (1 + len(self._all_score_criteria)))
                rows = []
                for i, scores in enumerate(batch_scores):
                    ext = extended_scores[i] if extended_scores and i < len(extended_scores) else {}
                    merged = {**scores, **ext}
                    rows.append((
                        first_offset + i,
                        *[merged.get(cid, 0.0) for cid in self._all_score_criteria],
                    ))
                self._conn.executemany(
                    f"INSERT OR REPLACE INTO schedule_scores (gidx, {col_list}) VALUES ({placeholders})",
                    rows,
                )

            self._conn.commit()

        # Move the global counter forward by the size of this batch. Done under
        # the dedicated count_lock (not self._lock) so the GUI thread's progress
        # poll never has to wait on the commit above.
        with self._count_lock:
            self._total_count += batch_count

    def _scores_for_ids(self, gidxs: List[int]) -> dict:
        """Read score dictionaries for the requested global schedule ids."""
        if not gidxs:
            return {}

        _col_map = {**_SCORE_COLS, **self._ext_feature_cols}
        cols = ", ".join(_col_map[cid] for cid in self._all_score_criteria)
        rows = []

        with self._lock:
            # SQLite has a limit on how many placeholders can be used in one query.
            # So we split the ids into safe chunks.
            for i in range(0, len(gidxs), 900):
                chunk = gidxs[i:i + 900]
                placeholders = ", ".join(["?"] * len(chunk))

                rows.extend(
                    self._conn.execute(
                        f"SELECT gidx, {cols} FROM schedule_scores WHERE gidx IN ({placeholders})",
                        chunk,
                    ).fetchall()
                )

        # Convert SQLite rows into {schedule_id: {criterion: score}}.
        return {
            row[0]: {cid: row[i + 1] for i, cid in enumerate(self._all_score_criteria)}
            for row in rows
        }

    def count_scores(self) -> int:
        """Return how many schedules have score rows saved."""
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM schedule_scores").fetchone()

        return int(row[0]) if row else 0

    def update_extended_scores(self, gidxs: List[int], score_rows: List[dict]) -> None:
        """Update lazily computed extension scores for existing schedules."""
        if not gidxs or not score_rows or not self._ext_feature_cols:
            return

        columns = [
            (feature_id, self._ext_feature_cols[feature_id])
            for feature_id in self._ext_feature_cols
        ]
        set_clause = ", ".join(f"{column} = ?" for _, column in columns)
        rows = []
        for gidx, scores in zip(gidxs, score_rows):
            rows.append((
                *[float(scores.get(feature_id, 0.0)) for feature_id, _ in columns],
                int(gidx),
            ))

        with self._lock:
            self._conn.executemany(
                f"UPDATE schedule_scores SET {set_clause} WHERE gidx = ?",
                rows,
            )
            self._conn.commit()

    def read_score_vectors(self, criteria: List[str], gidxs: List[int]) -> tuple:
        """Read score vectors for clustering without loading full schedules."""
        if not gidxs or not criteria:
            return [], np.empty((0, len(criteria)), dtype=float)
        col_map = {**_SCORE_COLS, **self._ext_feature_cols}
        cols = ", ".join(col_map[c] for c in criteria)
        all_rows: list = []

        with self._lock:
            # Split the query to avoid SQLite placeholder limits.
            for i in range(0, len(gidxs), 900):
                chunk = gidxs[i:i + 900]
                placeholders = ", ".join(["?"] * len(chunk))

                all_rows.extend(
                    self._conn.execute(
                        f"SELECT gidx, {cols} FROM schedule_scores"
                        f" WHERE gidx IN ({placeholders})",
                        chunk,
                    ).fetchall()
                )

        if not all_rows:
            return [], np.empty((0, len(criteria)), dtype=float)

        # Convert the SQL rows into a numpy matrix for fast numeric work.
        arr = np.array(all_rows, dtype=float)

        # Keep the ids sorted so the caller gets stable and predictable results.
        order = np.argsort(arr[:, 0], kind="stable")
        arr = arr[order]

        return arr[:, 0].astype(int).tolist(), arr[:, 1:]

    def _decode_batch(
        self,
        raw: bytes,
        first_offset: int,
        wanted_ids: "set[int] | None" = None,
    ) -> dict:
        """Decode one stored batch into {global_index: ScheduleDTO}."""
        # Every batch is compressed before it is saved.
        data = zlib.decompress(raw)

        # Old batches may be saved as normal pickled ScheduleDTO objects.
        if not is_packed_blob(data):
            batch: List[ScheduleDTO] = pickle.loads(data)

            if wanted_ids is None:
                return {first_offset + i: dto for i, dto in enumerate(batch)}

            return {
                first_offset + i: dto
                for i, dto in enumerate(batch)
                if first_offset + i in wanted_ids
            }

        # Packed schedules need the original slots to rebuild full DTO objects.
        if self._slots is None:
            raise RuntimeError("configure_slots() must be called before reading packed schedules")

        _slot_count, rows = unpack_rows(data)

        # Decode either the whole batch or only the ids we actually need.
        ids = (
            range(first_offset, first_offset + len(rows))
            if wanted_ids is None
            else sorted(g for g in wanted_ids if first_offset <= g < first_offset + len(rows))
        )

        # Add score data back into the DTOs if it exists.
        scores_by_id = self._scores_for_ids(list(ids))

        decoded = {}
        for gidx in ids:
            row = rows[gidx - first_offset]
            decoded[gidx] = row_to_dto(row, self._slots, scores_by_id.get(gidx))

        return decoded

    def clear(self) -> None:
        """Delete all saved schedules from the current run."""
        with self._lock:
            self._conn.execute("DELETE FROM schedule_batches")
            self._conn.execute("DELETE FROM schedule_scores")
            # Drop the lazily-built sort indexes too: keeping them would make the
            # next run's batch inserts pay index-maintenance cost for an order
            # nobody has asked for yet. They rebuild on the next sorted page.
            leftover_indexes = self._conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND name LIKE 'idx_sort_%'"
            ).fetchall()
            for (name,) in leftover_indexes:
                self._conn.execute(f"DROP INDEX IF EXISTS {name}")
            self._conn.commit()
        self._sort_index_signatures.clear()
        with self._count_lock:
            self._total_count = 0

    def get_window_raw(self, offset: int, limit: int) -> tuple:
        """Return raw rows for a page, without building full ScheduleDTO objects.

        The GUI can later build only the specific schedule it needs to display.
        This keeps page loading much faster when there are many results.
        """
        with self._lock:
            db_rows = self._conn.execute(
                "SELECT first_offset, batch_count, data FROM schedule_batches "
                "WHERE first_offset + batch_count > ? AND first_offset < ? ORDER BY first_offset",
                (offset, offset + limit),
            ).fetchall()

        raw_map: dict = {}

        for first_off, batch_count, raw_blob in db_rows:
            data = zlib.decompress(raw_blob)

            if is_packed_blob(data):
                _, rows = unpack_rows(data)

                # Take only the exact overlap between this batch and the requested page.
                lo = max(offset, first_off)
                hi = min(offset + limit, first_off + batch_count)

                for gidx in range(lo, hi):
                    raw_map[gidx] = rows[gidx - first_off]

            else:
                # Backward support for old batches that were saved as full DTOs.
                batch: List[ScheduleDTO] = pickle.loads(data)

                for i, dto in enumerate(batch):
                    gidx = first_off + i

                    if offset <= gidx < offset + limit:
                        raw_map[gidx] = dto

            if len(raw_map) >= limit:
                break

        # Scores are returned separately so the caller can attach them only when needed.
        score_map = self._scores_for_ids(list(raw_map.keys()))

        return raw_map, score_map, self._slots

    def ensure_sort_indexes(self, priority: List[str]) -> None:
        """Build a covering index matching one sort order, once per order.

        Without an index, get_sorted_ids_page re-runs a full ``ORDER BY`` with a
        temporary B-tree on every page, which costs ~1s at deep offsets on a
        large result set. A composite ``DESC`` index on exactly the requested
        columns turns that into a covering-index scan (gidx is the rowid, so it
        rides along for free) -- ~60x faster at deep offsets in measurements.

        Built lazily, on the first sorted page for a given priority, so the
        write-heavy generation path is never slowed by index maintenance. Each
        distinct sort order is indexed at most once; on-demand index count is
        therefore bounded by the number of sort orders the user actually picks.
        """
        if not priority:
            return  # No priority sorts by gidx (the primary key) -- already ordered.

        cols = [_SCORE_COLS[c] for c in priority]
        signature = ",".join(cols)
        if signature in self._sort_index_signatures:
            return

        index_name = "idx_sort_" + "_".join(cols)
        order = ", ".join(f"{col} DESC" for col in cols)
        with self._lock:
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON schedule_scores({order})"
            )
            self._conn.commit()
        self._sort_index_signatures.add(signature)

    def get_sorted_ids_page(
        self,
        priority: List[str],
        offset: int,
        limit: int,
    ) -> List[int]:
        """Return only one page of sorted ids using SQL LIMIT and OFFSET."""
        if priority:
            unknown = [c for c in priority if c not in _SCORE_COLS]
            if unknown:
                raise ValueError(
                    f"Unknown sort criteria: {', '.join(unknown)}. "
                    f"Valid criteria are: {', '.join(_SCORE_COLS)}."
                )

        # Make sure this sort order has a covering index before paging through it.
        self.ensure_sort_indexes(priority)

        with self._lock:
            if not priority:
                # No priority means regular order, but still only for this page.
                rows = self._conn.execute(
                    "SELECT gidx FROM schedule_scores ORDER BY gidx LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            else:
                # SQLite does the global sort, but returns only the page we asked for.
                order = ", ".join(f"{_SCORE_COLS[c]} DESC" for c in priority)
                rows = self._conn.execute(
                    f"SELECT gidx FROM schedule_scores ORDER BY {order} LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()

        return [r[0] for r in rows]

    def get_raw_by_ids(self, gidxs: List[int]) -> tuple:
        """Return raw schedule rows for any list of global ids."""
        if not gidxs:
            return {}, {}, self._slots

        # A set gives fast lookup when we scan the relevant batches.
        gidx_set = set(gidxs)

        # These bounds help us ask SQLite only for batches that may contain the ids.
        min_g, max_g = min(gidxs), max(gidxs)

        with self._lock:
            db_rows = self._conn.execute(
                "SELECT first_offset, batch_count, data FROM schedule_batches "
                "WHERE first_offset + batch_count > ? AND first_offset <= ? ORDER BY first_offset",
                (min_g, max_g),
            ).fetchall()

        raw_map: dict = {}

        for first_off, batch_count, raw_blob in db_rows:
            data = zlib.decompress(raw_blob)

            if is_packed_blob(data):
                _, rows = unpack_rows(data)

                # Scan the batch and keep only ids that were requested.
                for i, row in enumerate(rows):
                    gidx = first_off + i

                    if gidx in gidx_set and gidx not in raw_map:
                        raw_map[gidx] = row

            else:
                # Backward support for batches saved as full DTO objects.
                batch: List[ScheduleDTO] = pickle.loads(data)

                for i, dto in enumerate(batch):
                    gidx = first_off + i

                    if gidx in gidx_set and gidx not in raw_map:
                        raw_map[gidx] = dto

            if len(raw_map) >= len(gidxs):
                break

        # Return scores and slots together with the raw rows.
        score_map = self._scores_for_ids(list(raw_map.keys()))

        return raw_map, score_map, self._slots

    def get_schedules_by_ids(self, gidxs: List[int]) -> List[ScheduleDTO]:
        """Fetch full ScheduleDTO objects for the requested ids, in the same order."""
        if not gidxs:
            return []

        found: dict = {}
        batch_cache: dict = {}
        wanted_ids = set(gidxs)

        for g in gidxs:
            if g in found:
                continue

            with self._lock:
                # Find the single batch that contains this global schedule id.
                row = self._conn.execute(
                    "SELECT id, first_offset, batch_count, data FROM schedule_batches "
                    "WHERE first_offset <= ? AND first_offset + batch_count > ? LIMIT 1",
                    (g, g),
                ).fetchone()

            if row is None:
                continue

            batch_id, first_off, batch_count, raw = row

            # Decode each DB batch only once, even if we need several ids from it.
            if batch_id not in batch_cache:
                batch_wanted = {
                    w
                    for w in wanted_ids
                    if first_off <= w < first_off + batch_count
                }
                batch_cache[batch_id] = self._decode_batch(raw, first_off, batch_wanted)

            found.update(batch_cache[batch_id])

        # Preserve the order that the caller requested.
        return [found[g] for g in gidxs if g in found]

    def count(self) -> int:
        """Return how many schedules were saved in the current run."""
        with self._count_lock:
            return self._total_count
