"""Project-wide tunable constants."""

# Maximum number of study programs a user may select for one scheduling run.
MAX_PROGRAMS = 5

# Page size for HybridScheduleResultState's SQLite-backed result window.
WINDOW_SIZE = 10_000

# Safety cap on total schedules generated in one run.
DEFAULT_MAX_RESULTS = 1000000000000000000

# Number of schedules written to SQLite per batch during generation.
DEFAULT_BATCH_SIZE = 1_000

# Number of worker processes for schedule generation.
#   None  -> auto, detected from CPU topology (see CpuTopology.py):
#              hybrid CPU (has P/E split)  -> P-core count minus RESERVED_CORES_FOR_MAIN
#              non-hybrid CPU (no split)   -> every physical core, unreduced
#            The reservation below only makes sense once we know which cores
#            are the fast ones, so it never shrinks the non-hybrid default.
#   int   -> force exactly this many workers.
# The environment variable SCHEDULER_WORKER_PROCESSES overrides this at runtime.
# Measured (god_balanced, 1M, i7-13620H = 6 P-cores + 4 E-cores): the old
# "all physical cores" default (10) took ~65s; 4 workers took ~43s (-34%).
# Using every physical core puts workers on slow E-cores (stragglers) and
# saturates a laptop into thermal throttling under sustained load. This
# tuning is specific to hybrid CPUs -- it has not been measured on other
# core counts or on non-hybrid hardware.
WORKER_PROCESS_COUNT = None

# Pin each worker to a P-core. OFF by default: measurement showed static pinning
# HELPS short runs but HURTS large ones (1M: pinned 4 = ~52s vs unpinned 4 = ~43s)
# because it denies the OS the freedom to spread workers across all P-cores and
# rotate them off hot cores. Kept as an opt-in knob; no effect on non-hybrid CPUs.
WORKER_AFFINITY_ENABLED = False

# P-cores to leave free for the main process (GUI + SQLite writer thread + work
# feeder + result-queue drain) when auto-sizing the pool on a HYBRID CPU only.
# On the 6-P-core test machine, reserving 2 lands on the measured-optimal 4
# workers and keeps the write pipeline fed. This is a flat offset tuned for
# that one machine, not a validated ratio -- on a hybrid CPU with very few
# P-cores it can floor the pool to 1 worker; re-measure before trusting it
# elsewhere. Never applied on non-hybrid CPUs (see CpuTopology.recommended_worker_count).
RESERVED_CORES_FOR_MAIN = 2

# We create more work units than processes, so workers can grab another unit when they finish early.
WORK_UNITS_PER_WORKER = 8

# Result queue size, counted in pending result batches per worker (not individual schedules).
RESULT_QUEUE_BATCHES_PER_WORKER = 4

# Do not split the search-space partitioner too deep, because partitioning itself should stay cheap.
MAX_PARTITION_DEPTH = 4

# Max number of decoded ScheduleDTOs HybridScheduleResultState keeps cached per page.
SCHEDULE_DTO_CACHE_SIZE = 32

# How often AppController polls the repository count during an active generation run.
PROGRESS_POLL_INTERVAL_MS = 500
