"""Project-wide tunable constants."""

# Maximum number of study programs a user may select for one scheduling run.
MAX_PROGRAMS = 5

# Page size for HybridScheduleResultState's SQLite-backed result window.
WINDOW_SIZE = 10_000

# Safety cap on total schedules generated in one run.
DEFAULT_MAX_RESULTS = 1_000_000

# Number of schedules written to SQLite per batch during generation.
DEFAULT_BATCH_SIZE = 1_000

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
