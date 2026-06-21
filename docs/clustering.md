# K-Clustering — Design & Architecture

This document describes the clustering feature added under `src/logic/clustering`
and `src/application/services/ClusteringCoordinator.py`. It covers what was built
in this first pass (the **default** path, no LLM), the data flow, the trade-offs,
and exactly where the future LLM / free-text step plugs in.

## 1. Goal

A scheduling run can produce hundreds of thousands of valid schedules. Browsing
them one by one is hopeless. Clustering groups them into a handful of
representative **families** (archetypes), each with a one-line description, so the
user gets an immediate high-level picture and can then drill into a family and
keep using the existing sort controls.

This pass implements the default, zero-configuration behaviour: open the screen →
schedules are clustered automatically with an auto-chosen K → families are shown
with counts and descriptions. The LLM / custom free-text step is intentionally
**not** here yet, but the whole engine is shaped so it drops in without change.

## 2. Key design decision: reuse the five existing scores

The earlier prototype (the uploaded `cluster.zip`) recomputed date-based features
(compactness, weekend usage, gaps, dispersion…) from each schedule. The current
system already computes **five scores per schedule** during generation, stored on
`ScheduleDTO.scores` and in the SQLite `schedule_scores` table:

| Criterion | Meaning (higher = better) |
|---|---|
| `MIN_MANDATORY_GAP` | smallest gap between mandatory exams |
| `AVG_ALL_COURSES_GAP` | average gap across all courses |
| `ELECTIVE_CONFLICTS` | elective clashes (negated) |
| `MANDATORY_SPAN` | span of the mandatory exams |
| `MAX_EXAMS_PER_DAY` | busiest-day load (negated) |

So the feature vector **is** the score vector. This is the central adaptation:

- **No recomputation** — the expensive per-schedule work is already done.
- **Consistency** — clustering and sorting see the same numbers.
- **Scale** — the `schedule_scores` table (`gidx, s_0..s_4`) lets the pipeline
  read score vectors straight from SQL **without unpickling a single schedule**.

## 3. Architecture (Strategy pattern, preserved from the prototype)

The prototype's clean Strategy decomposition was kept; each stage is an
independent, swappable component:

```
            ┌──────────────────────── ClusteringCoordinator ────────────────────────┐
            │  (application layer: knows where vectors live — SQLite / in-memory)    │
            └───────────────┬───────────────────────────────────────────────────────┘
                            │ sampled score vectors (n, 5)
                            ▼
   ScheduleSampler ──▶ ScoreFeatureExtractor ──▶ FeatureNormalizer ──▶ AutoKSelector ──▶ KMeansClusteringStrategy
   (≤ max_sample)      (scores → vector)         (min-max → [0,1])     (silhouette → K)   (k-means++, in-house)
                            │                                                                     │
                            ▼                                                                     ▼
                     ClusterSummarizer  ◀────────────  ClusteringService (orchestrator)  ──▶  ClusterResult
                     (stats → sentence)                                                        (families + reps)
```

### Components

| File | Role |
|---|---|
| `ClusterConfig` | The single contract describing one run: criteria, weights, K mode, sampling, seed. **This is the object the future LLM produces.** |
| `IFeatureExtractor` / `ScoreFeatureExtractor` | Turn a schedule (or a bare score map) into a vector, in a fixed criterion order. |
| `FeatureNormalizer` | Min-max each dimension to `[0,1]` so no score dominates the distance. |
| `IDistanceMetric` / `EuclideanDistanceMetric` / `WeightedEuclideanDistanceMetric` | Similarity in normalized space. The weighted metric is what "group mostly by X" will use. |
| `IClusteringStrategy` / `KMeansClusteringStrategy` | The algorithm. In-house k-means++ (deterministic, no scikit-learn dependency), swappable. |
| `AutoKSelector` | Picks K by mean **silhouette** over a candidate range, evaluated on a capped sub-sample for speed. |
| `ScheduleSampler` | Uniform representative sample (≤ `max_sample`) so the pipeline stays fast at scale. |
| `ClusterSummarizer` | Default, dependency-free one-line descriptions from simple statistics. |
| `Cluster` / `ClusterResult` | Plain, picklable result models (families, representatives, population estimates). |
| `ClusteringService` | Orchestrates extract → normalize → choose-K → cluster → representatives → summarize. |
| `ClusteringCoordinator` | Application driver: samples ids, reads score vectors from the repository, runs the service, maps working positions back to global schedule ids for drill-down. |

## 4. Data flow at scale

1. **Sample** — `ScheduleSampler` draws up to `max_sample` (default 10,000) ids
   from the population (`repository.count_scores()`).
2. **Read vectors** — `repository.read_score_vectors(criteria, ids)` pulls only
   the `schedule_scores` rows (no schedule materialised).
3. **Normalize** — min-max to `[0,1]`.
4. **Choose K** — silhouette over `[k_min, k_max]`, evaluated on a capped subset
   (silhouette is O(n²), so this keeps auto-K cheap).
5. **Cluster** — k-means++ on the full working set with the chosen K.
6. **Representatives & profiles** — each family's archetype is the member nearest
   its centroid; per-cluster sizes are scaled back up to the full population.
7. **Summaries** — `ClusterSummarizer` turns each family's profile into a
   sentence (e.g. *"Mandatory exams packed close together; a heavy busiest-day
   load"*).

Drill-down: `ClusteringRun.gidx_for(cluster.member_indices)` maps a family's
member positions to global schedule ids, which the existing
`repository.get_raw_by_ids(...)` fetches — and the existing sort still applies,
because sorting a family is just sorting that id slice.

## 5. Trade-offs

- **In-house k-means vs scikit-learn.** Kept in-house to avoid a new dependency
  and keep the algorithm explicit and deterministic. The `IClusteringStrategy`
  seam means a `SklearnKMeansStrategy` can be dropped in later with no caller
  change if desired.
- **Silhouette for auto-K.** More reliable than the elbow heuristic, but O(n²);
  mitigated by evaluating on a capped sub-sample (`max_eval_points`, default
  2000). The final clustering still runs on the full working set.
- **Uniform sampling.** Simple and representative in expectation; very small
  families could be missed. Stratified sampling is a future swap behind the same
  `ScheduleSampler` seam.
- **Reusing scores as features.** Fast and consistent, but clustering is only as
  expressive as those five scores. Adding a feature later means adding a score
  criterion (or a different `IFeatureExtractor`).

## 6. Where the LLM / free-text step plugs in (next phase)

Nothing in the engine needs to change. The future custom-clustering UI / LLM
layer only has to produce a `ClusterConfig`:

```python
# future: translate_request_to_config(text) -> ClusterConfig
cfg = ClusterConfig(
    criteria=(MANDATORY_SPAN, MAX_EXAMS_PER_DAY),  # "group by spread & daily load"
    weights={MANDATORY_SPAN: 3.0},                 # "mostly by spread"
    k_mode="fixed", k=4,                            # "give me 4 groups"
)
cfg.validate()                                      # future: validate_config(config)
run = ClusteringCoordinator(repository).run(cfg)    # same engine, no change
```

`ClusterConfig.validate()` is already the `validate_config` step; falling back to
`ClusterConfig.default()` on an LLM failure is the graceful-fallback step. The
`ClusterSummarizer` contract (`Cluster -> str`) is where an LLM summary would
replace the statistical one.

## 7. Tests & demo

- `tests/logic/unit/test_clustering_engine.py` — component-level tests (extractor,
  normalizer, metrics, k-means, auto-K range, summarizer, service coverage).
- `tests/logic/integration/test_clustering_pipeline.py` — full pipeline, both
  in-memory and repository-backed (real temp SQLite), full-coverage and
  gidx-mapping checks.
- `tests/performance/test_clustering_performance.py` — 50,000-schedule population
  clustered end-to-end well within budget (`@pytest.mark.performance`).
- `scripts/clustering_demo.py` — headless demo: builds a synthetic population with
  planted archetypes and prints the recovered families.

```
python scripts/clustering_demo.py
python -m pytest tests/logic/unit/test_clustering_engine.py tests/logic/integration/test_clustering_pipeline.py
python -m pytest -m performance tests/performance/test_clustering_performance.py
```

## 8. Not in this pass (by design)

- PyQt cluster screen, drill-down UI, in-cluster sort wiring (UI layer).
- LLM translation, free-text input field, loading states.
- Re-clustering on settings change.

These sit on top of the finished engine and coordinator without re-touching them.
