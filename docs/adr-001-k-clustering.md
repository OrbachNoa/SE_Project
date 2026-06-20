# ADR-001: K-Clustering of Generated Schedules

**Status:** Accepted (default/non-LLM pass)
**Date:** 2026-06-20
**Deciders:** enav (project owner)
**Related:** Jira epic SCRUM-278 (used as conceptual reference only, not as binding spec)

---

## Context

A scheduling run can yield hundreds of thousands of valid schedules. Browsing them
one at a time is impractical, so we want to group them into a few representative
**families** (archetypes), each with a short description, shown automatically on
screen entry. The user can then drill into a family and keep using the existing
sort controls.

Forces at play:

- **Scale** — up to ~10⁵–10⁶ schedules; the pipeline must stay responsive.
- **Existing assets** — every schedule is already scored on 5 sort criteria
  (`MIN_MANDATORY_GAP`, `AVG_ALL_COURSES_GAP`, `ELECTIVE_CONFLICTS`,
  `MANDATORY_SPAN`, `MAX_EXAMS_PER_DAY`), stored on `ScheduleDTO.scores` and in the
  SQLite `schedule_scores` table (`gidx, s_0..s_4`).
- **Prior art** — an uploaded prototype (`cluster.zip`) with a clean Strategy-based
  clustering engine that recomputed date-based features and used an in-house
  K-means.
- **Future direction** — a later phase adds an LLM + free-text box so users can
  describe a grouping in natural language; this pass must not paint that into a
  corner.
- **Constraint** — this pass delivers the **default** path only (auto K, default
  criteria, statistical summaries); no LLM, no PyQt UI yet.

This ADR records the decisions taken while building `src/logic/clustering` and
`src/application/services/ClusteringCoordinator.py`.

---

## Decision (summary)

Build a Strategy-based clustering engine that **reuses the 5 precomputed scores as
the feature vector**, runs an **in-house K-means** (behind a swappable interface)
with **silhouette-based automatic K** on a **uniformly sampled** working set read
**directly from SQLite**, and produces **rule-based statistical summaries**. All
behaviour is driven by a single `ClusterConfig` object that the future LLM layer
will emit unchanged.

The individual decisions follow.

---

## Decision 1 — Feature source: reuse existing scores

**Choice: the feature vector *is* the 5-score vector. Do not recompute.**

| Option | Complexity | Cost (per run) | Consistency | Verdict |
|---|---|---|---|---|
| A. Reuse the 5 precomputed scores | Low | ~0 (already computed) | Same numbers as sort | **Chosen** |
| B. Recompute date-based features (prototype) | Med | High (re-parse every schedule) | Separate from sort | Rejected |

**Why:** the scores already capture a schedule's character, are stored, and are
read cheaply from SQL. Reusing them keeps clustering fast and consistent with how
the app ranks. **Cons:** clustering is only as expressive as those 5 scores; adding
expressiveness means adding a criterion or a different `IFeatureExtractor`
(the interface makes that a drop-in).

## Decision 2 — Algorithm: in-house K-means behind a Strategy

**Choice: in-house k-means++ as the default `IClusteringStrategy`; no scikit-learn.**

| Option | Complexity | New dependency | Determinism | Verdict |
|---|---|---|---|---|
| A. In-house k-means++ behind `IClusteringStrategy` | Low–Med | None | Fully (fixed seed) | **Chosen** |
| B. scikit-learn `KMeans` | Low | scikit-learn + transitive | Yes | Rejected for now |
| C. Hierarchical / k-medoids | High | Maybe | Varies | Out of scope |

**Why:** keeps the project lightweight (only numpy, already used), the algorithm
explicit and deterministic (stable UI), and faithful to the prototype. The Jira
ticket asked for scikit-learn, but the user confirmed Jira is reference-only — so
familiarity and zero-dependency won. The `IClusteringStrategy` seam means a
`SklearnKMeansStrategy` can replace it later with **no caller change**.

## Decision 3 — Automatic K via silhouette on a capped sub-sample

**Choice: pick K in `[k_min, k_max]` by best mean silhouette, evaluated on ≤2000 points.**

| Option | Quality | Cost | Verdict |
|---|---|---|---|
| A. Silhouette, capped eval subset | Good | O(m²), m capped | **Chosen** |
| B. Silhouette on full working set | Good | O(n²) — too slow at 10K | Rejected |
| C. Elbow / inertia knee | Heuristic | Cheap | Rejected (less robust) |

**Why:** silhouette is more reliable than the elbow heuristic; capping the
evaluation subset removes its O(n²) cost while the **final** clustering still runs
on the full working set. **Revisit if** families are very imbalanced (silhouette
can under-count tiny clusters).

## Decision 4 — Uniform sampling to bound work

**Choice: uniform random sample of up to `max_sample` (default 10,000); scale counts back up.**

| Option | Representativeness | Complexity | Verdict |
|---|---|---|---|
| A. Uniform sample ≤ max_sample | Good in expectation | Low | **Chosen** |
| B. Cluster the full population | Exact | Too slow | Rejected |
| C. Stratified sample | Better for rare families | Higher | Future swap |

**Why:** keeps K-means and auto-K fast at any scale; per-cluster sizes are scaled
by `population/working_set` to estimate full-population counts. Sampling is an
explicit, documented step (`ScheduleSampler`) so it can be swapped for stratified
sampling later. **Cons:** very small families may be missed.

## Decision 5 — Read score vectors directly from SQLite

**Choice: add `count_scores()` + `read_score_vectors(criteria, gidxs)` to the repository; build the feature matrix from the `schedule_scores` table without unpickling schedules.**

**Why:** the narrow score table already holds everything clustering needs. Reading
vectors straight from SQL avoids decompressing/unpickling thousands of
`ScheduleDTO`s — the single biggest performance lever. The two methods are
**purely additive** (36 lines, 0 deletions) to `SQLiteScheduleRepository`.
Drill-down maps a family's working positions back to global ids via
`ClusteringRun.gidx_for(...)`, reusing the existing `get_raw_by_ids(...)`.

## Decision 6 — Statistical (non-LLM) cluster summaries

**Choice: `ClusterSummarizer` produces one-line descriptions from simple z-score rules across clusters.**

| Option | Quality | Dependency | Reliability | Verdict |
|---|---|---|---|---|
| A. Rule-based statistical | Good enough | None | Cannot fail the screen | **Chosen (default)** |
| B. LLM-generated | Richer prose | Network/LLM | Can fail/slow | Deferred to next phase |

**Why:** the default path must work offline and never blank the screen. Summary
failures are swallowed (a cluster simply shows no description). The contract is
`Cluster -> str`, so an LLM summarizer drops in later behind the same method.

## Decision 7 — `ClusterConfig` as the single seam for the future LLM

**Choice: every run is described by one validated `ClusterConfig` (criteria, weights, K mode, sampling, seed).**

**Why:** today it is filled with defaults; tomorrow the LLM/free-text layer emits
the same object from natural language and nothing downstream changes.
`ClusterConfig.validate()` is already the future `validate_config` step, and
`ClusterConfig.default()` is the graceful fallback when an LLM response is invalid.
A `WeightedEuclideanDistanceMetric` was added so requests like "group mostly by
exam spread" map onto `weights` with no algorithm change.

## Decision 8 — Scope boundary for this pass

**Choice: deliver engine + application coordinator + tests + headless demo; defer PyQt UI and LLM.**

**Why:** the testable core delivers the value and de-risks the rest. The UI
(cluster screen, drill-down, in-cluster sort) and the LLM step sit on top without
re-touching the engine.

---

## Trade-off Analysis

The through-line is **leverage what exists**: reuse the scores, read them from the
table already on disk, and keep the algorithm dependency-free and deterministic.
We trade some expressiveness (limited to 5 scores) and exactness (sampling) for
speed, simplicity, and consistency with the rest of the app. Every place where a
richer-but-heavier choice was rejected (scikit-learn, full-population silhouette,
LLM summaries, stratified sampling) sits behind an interface, so upgrading later is
a swap, not a rewrite.

## Consequences

**Easier:**
- Clustering is fast at scale and deterministic.
- The future LLM/custom-clustering phase is a `ClusterConfig` producer — no engine change.
- Each stage (extractor, metric, strategy, sampler, summarizer) is independently testable and swappable.

**Harder / watch:**
- Clustering quality is bounded by the 5 scores.
- Uniform sampling can miss rare families; revisit with stratified sampling if needed.
- Silhouette auto-K can be conservative on imbalanced data.

**To revisit as the system grows:**
- Swap to scikit-learn or another strategy if requirements demand it.
- Stratified sampling for rare-family fidelity.
- LLM-backed summaries and free-text config translation.

## Action Items

1. [x] Build engine (`src/logic/clustering/*`) with Strategy components.
2. [x] Reuse 5 scores; add SQLite `count_scores` / `read_score_vectors`.
3. [x] Auto-K (silhouette), uniform sampler, statistical summarizer.
4. [x] `ClusteringCoordinator` + `ClusterConfig` seam for the future LLM.
5. [x] Unit + integration + performance tests; headless demo.
6. [ ] Wire the PyQt cluster screen (list, drill-down, in-cluster sort).
7. [ ] LLM phase: `translate_request_to_config(text) -> ClusterConfig`, free-text UI, loading states, graceful fallback.

## Verification (this pass)

- 23 unit + integration tests pass (incl. real temp-SQLite pipeline).
- Performance test: 50,000 schedules clustered end-to-end in ~4.4 s.
- Repository change is additive only (36 insertions, 0 deletions).
