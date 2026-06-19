"""Formats the diagnostics gathered from worker FINISHED payloads into one
human-readable summary table. Shared by SchedulerWorker (real app runs) and
the benchmarks/ scripts (manual profiling), so both print the same shape.
"""
from __future__ import annotations

from typing import List, Optional


def _aggregate_checker_stats(worker_stats: List[dict]) -> List[dict]:
    """Sums per-checker call/reject counts across every process that reported
    them, keyed by (name, scope, k) since that identifies one logical checker
    even though each process built its own separate instance.
    """
    totals: dict = {}
    order: List[tuple] = []
    for ws in worker_stats:
        for cs in ws.get("checker_stats") or []:
            key = (cs["name"], cs.get("scope"), cs.get("k"))
            if key not in totals:
                totals[key] = {"calls": 0, "rejects": 0}
                order.append(key)
            totals[key]["calls"] += cs["calls"]
            totals[key]["rejects"] += cs["rejects"]
    return [
        {"name": k[0], "scope": k[1], "k": k[2], "calls": totals[k]["calls"], "rejects": totals[k]["rejects"]}
        for k in order
    ]


def format_summary(
    worker_stats: List[dict],
    elapsed_s: float,
    sqlite_write_ms_total: float = 0.0,
    sqlite_write_count: int = 0,
    partition_time_s: Optional[float] = None,
    leftover_cubes: Optional[int] = None,
) -> str:
    """Builds the full diagnostics table as one string, ready to print.

    elapsed_s covers everything from process spawn to last FINISHED. Cube
    generation now runs on its own thread, started right alongside the
    processes (see generate_async / _feed_work_queue) instead of blocking
    before any process exists - so partition_time_s is NESTED inside
    elapsed_s, overlapping with process startup, not a separate preceding
    window. The percentage below is how much of that overlap window the
    partitioner used, not extra time added on top.
    """
    lines = []
    lines.append("=== Diagnostics summary ===")
    lines.append(f"total elapsed:         {elapsed_s:.3f}s")
    if partition_time_s is not None:
        pct = 100 * partition_time_s / elapsed_s if elapsed_s else 0
        lines.append(f"partitioner time:      {partition_time_s:.3f}s ({pct:.1f}% of total - "
                      f"runs on its own thread, overlapped with process startup, not before it)")
    if leftover_cubes is not None:
        lines.append(f"leftover work units:  {leftover_cubes} (never pulled by any process - "
                      f"{'0 = partition was exactly right' if leftover_cubes == 0 else 'partition produced more units than needed'})")

    num_processes = len(worker_stats) or 1
    total_blocked = sum(ws.get("blocked_puts", 0) for ws in worker_stats)
    total_lock_wait_ms = sum(ws.get("lock_wait_ms_total", 0.0) for ws in worker_stats)
    lock_wait_pct_of_wall = 100 * (total_lock_wait_ms / 1000) / (elapsed_s * num_processes) if elapsed_s else 0

    lines.append("")
    lines.append(f"blocked put() calls (results queue full): {total_blocked}")
    lines.append(f"result_counter lock-wait: {total_lock_wait_ms:.1f}ms total across "
                  f"{num_processes} processes ({lock_wait_pct_of_wall:.2f}% of aggregate process time)")

    sqlite_pct = 100 * (sqlite_write_ms_total / 1000) / elapsed_s if elapsed_s else 0
    lines.append(f"SQLite insert_compressed_batch: {sqlite_write_ms_total:.1f}ms total over "
                  f"{sqlite_write_count} calls ({sqlite_pct:.2f}% of wall time)")

    overhead_ms = total_lock_wait_ms + sqlite_write_ms_total
    overhead_pct = 100 * (overhead_ms / 1000) / elapsed_s if elapsed_s else 0
    lines.append(f"measured overhead (lock-wait + SQLite, NOT pure CPU search time): "
                  f"{overhead_ms:.1f}ms ({overhead_pct:.2f}% of wall time)")

    lines.append("")
    lines.append("--- per-process work (cubes/schedules - look for imbalance) ---")
    total_found = sum(ws.get("schedules_found", 0) for ws in worker_stats)
    for ws in sorted(worker_stats, key=lambda w: -w.get("schedules_found", 0)):
        found = ws.get("schedules_found", 0)
        pct = 100 * found / total_found if total_found else 0
        cubes = ws.get("cubes_processed")
        cubes_str = str(cubes) if cubes is not None else "n/a (static strategy)"
        lines.append(f"  pid={ws.get('pid', '?'):>7}  cubes={cubes_str:>20}  "
                      f"schedules_found={found:>9} ({pct:5.1f}%)")

    checker_stats = _aggregate_checker_stats(worker_stats)
    if checker_stats:
        lines.append("")
        lines.append("--- per-checker rejection rate (the single most actionable metric for "
                      "checker-order optimization) ---")
        for cs in sorted(checker_stats, key=lambda c: -(c["rejects"] / c["calls"] if c["calls"] else 0)):
            rate = 100 * cs["rejects"] / cs["calls"] if cs["calls"] else 0
            label = cs["name"]
            if cs["scope"]:
                label += f"({cs['scope']},k={cs['k']})"
            lines.append(f"  {label:45s} calls={cs['calls']:>10} rejects={cs['rejects']:>10} rate={rate:6.2f}%")

    return "\n".join(lines)
