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

_DEFAULT_DB = os.path.join(tempfile.gettempdir(), "exam_scheduler_overflow.sqlite")
_SCORE_COLS = {cid: f"s_{i}" for i, cid in enumerate(ALL_CRITERIA)}


class SQLiteScheduleRepository:
    """Stores ScheduleDTO objects in batched, compressed SQLite rows."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = db_path
        self._total_count: int = 0
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection = self._open_connection()
        self._slots = None
        self._init_db()

    def configure_slots(self, slots: list) -> None:
        """Provide slot metadata needed to lazily materialize packed schedules."""
        self._slots = list(slots)

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schedule_batches ("
                "    id            INTEGER PRIMARY KEY AUTOINCREMENT,"
                "    first_offset  INTEGER NOT NULL,"
                "    batch_count   INTEGER NOT NULL,"
                "    data          BLOB    NOT NULL"
                ")"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_offset "
                "ON schedule_batches(first_offset)"
            )
            score_cols = ", ".join(f"{c} REAL" for c in _SCORE_COLS.values())
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS schedule_scores ("
                f"    gidx INTEGER PRIMARY KEY, {score_cols})"
            )
            self._conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────

    def insert_batch(self, batch: List[ScheduleDTO]) -> None:
        data = zlib.compress(pickle.dumps(batch, protocol=4), level=1)
        self.insert_compressed_batch(data, len(batch))

    def insert_compressed_batch(self, data: bytes, batch_count: int,
                                batch_scores: "List[dict] | None" = None) -> None:
        with self._lock:
            first_offset = self._total_count
            self._conn.execute(
                "INSERT INTO schedule_batches (first_offset, batch_count, data) VALUES (?, ?, ?)",
                (first_offset, batch_count, data),
            )
            if batch_scores:
                placeholders = ", ".join(["?"] * (1 + len(ALL_CRITERIA)))
                rows = [
                    (first_offset + i, *[scores.get(cid, 0.0) for cid in ALL_CRITERIA])
                    for i, scores in enumerate(batch_scores)
                ]
                self._conn.executemany(
                    f"INSERT OR REPLACE INTO schedule_scores VALUES ({placeholders})", rows,
                )
            self._conn.commit()
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
        return {row[0]: {cid: row[i + 1] for i, cid in enumerate(ALL_CRITERIA)} for row in rows}

    # ── Clustering support: cheap score-vector reads ───────────────────────

    def count_scores(self) -> int:
        """Number of schedules that have a stored score row.

        gidx values are assigned contiguously from 0, so this doubles as the
        population size the clustering sampler draws indices from.
        """
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM schedule_scores").fetchone()
        return int(row[0]) if row else 0

    def read_score_vectors(self, criteria: List[str], gidxs: List[int]) -> tuple:
        """Read score vectors for the given gidxs, projected onto ``criteria``.

        Returns ``(ids, vectors)`` where ``ids`` are the gidxs actually found (in
        ascending order) and ``vectors[i]`` is the score vector for ``ids[i]`` in
        ``criteria`` order. Reads only the narrow ``schedule_scores`` table, so
        building the clustering feature matrix never unpickles a schedule.
        """
        if not gidxs or not criteria:
            return [], []
        cols = ", ".join(_SCORE_COLS[c] for c in criteria)
        found: dict = {}
        with self._lock:
            for i in range(0, len(gidxs), 900):
                chunk = gidxs[i:i + 900]
                placeholders = ", ".join(["?"] * len(chunk))
                for row in self._conn.execute(
                    f"SELECT gidx, {cols} FROM schedule_scores WHERE gidx IN ({placeholders})",
                    chunk,
                ).fetchall():
                    found[row[0]] = [float(v) for v in row[1:]]
        ids = sorted(found)
        return ids, [found[g] for g in ids]

    def _decode_batch(self, raw: bytes, first_offset: int, wanted_ids: "set[int] | None" = None) -> dict:
        """Decode one stored batch into {global_index: ScheduleDTO}."""
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
            raise RuntimeError("configure_slots() must be called before reading packed schedules")
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
        with self._lock:
            self._total_count = 0
            self._conn.execute("DELETE FROM schedule_batches")
            self._conn.execute("DELETE FROM schedule_scores")
            self._conn.commit()

    # ── Read ───────────────────────────────────────────────────────────────

    def get_window(self, offset: int, limit: int) -> List[ScheduleDTO]:
        """Returns a position-based window of schedules."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT first_offset, batch_count, data FROM schedule_batches "
                "WHERE first_offset + batch_count > ? AND first_offset < ? ORDER BY first_offset",
                (offset, offset + limit),
            ).fetchall()
        wanted = set(range(offset, offset + limit))
        result_by_id: dict = {}
        for first_off, batch_count, raw in rows:
            overlap = {g for g in wanted if first_off <= g < first_off + batch_count}
            result_by_id.update(self._decode_batch(raw, first_off, overlap))
            if len(result_by_id) >= limit:
                break
        return [result_by_id[g] for g in range(offset, offset + limit) if g in result_by_id]

    def get_window_raw(self, offset: int, limit: int) -> tuple:
        """Like get_window() but returns raw packed tuples instead of ScheduleDTOs.

        Returns (raw_map, score_map, slots).  The caller calls row_to_dto()
        lazily for only the one schedule it needs to display, cutting page-load
        time from ~2 s to ~50 ms.
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
                # Compute the exact overlap range instead of checking each of
                # `limit` IDs against the batch bounds — O(overlap) not O(limit).
                lo = max(offset, first_off)
                hi = min(offset + limit, first_off + batch_count)
                for gidx in range(lo, hi):
                    raw_map[gidx] = rows[gidx - first_off]
            else:
                batch: List[ScheduleDTO] = pickle.loads(data)
                for i, dto in enumerate(batch):
                    gidx = first_off + i
                    if offset <= gidx < offset + limit:
                        raw_map[gidx] = dto
            if len(raw_map) >= limit:
                break
        score_map = self._scores_for_ids(list(raw_map.keys()))
        return raw_map, score_map, self._slots

    # ── Option B: global sort + lazy fetch ─────────────────────────────────

    def get_sorted_ids(self, priority: List[str]) -> List[int]:
        """Returns ALL schedule ids sorted by the given priority list (descending).

        Reads only the narrow score table so the sort is fast even for 10,000+
        schedules.  Returns a lightweight list of integers; the caller holds
        this in memory and fetches raw rows for any page slice on demand.
        """
        with self._lock:
            if not priority:
                rows = self._conn.execute("SELECT gidx FROM schedule_scores ORDER BY gidx").fetchall()
            else:
                order = ", ".join(f"{_SCORE_COLS[c]} DESC" for c in priority)
                rows = self._conn.execute(
                    f"SELECT gidx FROM schedule_scores ORDER BY {order}"
                ).fetchall()
        return [r[0] for r in rows]

    def get_sorted_ids_page(self, priority: List[str], offset: int, limit: int) -> List[int]:
        """Return ONE page of globally-sorted ids using SQL LIMIT/OFFSET.

        SQLite still sorts the whole score table (so the result is the true
        global top-K for this page), but only transfers `limit` ids back instead
        of all ~1M. That makes a sort ~8x faster (e.g. ~150ms vs ~1.2s at 1M),
        because the cost was dominated by hauling every id into Python, not by
        the sort itself.
        """
        with self._lock:
            if not priority:
                rows = self._conn.execute(
                    "SELECT gidx FROM schedule_scores ORDER BY gidx LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            else:
                order = ", ".join(f"{_SCORE_COLS[c]} DESC" for c in priority)
                rows = self._conn.execute(
                    f"SELECT gidx FROM schedule_scores ORDER BY {order} LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [r[0] for r in rows]

    def get_raw_by_ids(self, gidxs: List[int]) -> tuple:
        """Like get_window_raw() but for an arbitrary list of global ids.

        Used by the sorted lazy path: given the page slice of sorted_ids, returns
        (raw_map, score_map, slots) without materialising any ScheduleDTO.
        raw_map is keyed by global_index, same contract as get_window_raw().
        """
        if not gidxs:
            return {}, {}, self._slots
        gidx_set = set(gidxs)
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
                # Iterate the (small) batch, not the (large) gidx_set.
                # O(batch_count) set-lookup vs O(|gidx_set|) range-check per batch.
                for i, row in enumerate(rows):
                    gidx = first_off + i
                    if gidx in gidx_set and gidx not in raw_map:
                        raw_map[gidx] = row
            else:
                batch: List[ScheduleDTO] = pickle.loads(data)
                for i, dto in enumerate(batch):
                    gidx = first_off + i
                    if gidx in gidx_set and gidx not in raw_map:
                        raw_map[gidx] = dto
            if len(raw_map) >= len(gidxs):
                break
        score_map = self._scores_for_ids(list(raw_map.keys()))
        return raw_map, score_map, self._slots

    def get_schedules_by_ids(self, gidxs: List[int]) -> List[ScheduleDTO]:
        """Fetches full ScheduleDTOs for the given global ids, preserving their order.

        Used for ad-hoc lookups; prefer get_raw_by_ids() + lazy row_to_dto()
        for large page loads to avoid materialising thousands of DTOs at once.
        """
        if not gidxs:
            return []
        found: dict = {}
        batch_cache: dict = {}
        wanted_ids = set(gidxs)
        for g in gidxs:
            if g in found:
                continue
            with self._lock:
                row = self._conn.execute(
                    "SELECT id, first_offset, batch_count, data FROM schedule_batches "
                    "WHERE first_offset <= ? AND first_offset + batch_count > ? LIMIT 1",
                    (g, g),
                ).fetchone()
            if row is None:
                continue
            batch_id, first_off, batch_count, raw = row
            if batch_id not in batch_cache:
                batch_wanted = {w for w in wanted_ids if first_off <= w < first_off + batch_count}
                batch_cache[batch_id] = self._decode_batch(raw, first_off, batch_wanted)
            found.update(batch_cache[batch_id])
        return [found[g] for g in gidxs if g in found]

    def count(self) -> int:
        """Returns how many schedules were saved in the current run."""
        with self._lock:
            return self._total_count