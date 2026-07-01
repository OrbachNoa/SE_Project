# Clustering Overview & Architecture

This document describes the clustering engine (`src/logic/clustering`) and how it groups hundreds of thousands of generated schedules into a handful of representative **families** (archetypes).

## 1. Goal & Approach

A scheduling run can produce vast amounts of valid schedules. Browsing them one by one is impractical. Instead, the system groups them by similarity into families so the user gets an immediate high-level picture. 

**Key Design Choice: Reuse Existing Scores**
Rather than re-parsing schedules to compute features, the feature vector *is* the array of precomputed criteria scores (e.g., `MIN_MANDATORY_GAP`, `MAX_EXAMS_PER_DAY`, etc.) generated during the initial scheduler run. 
Because these are stored directly in the `schedule_scores` SQLite table, the pipeline reads score vectors directly from SQL **without unpickling a single schedule**. This makes clustering highly performant.

## 2. Architecture & Data Flow

The engine uses a Strategy-based design, preserving a clean pipeline of independent, swappable components:

```text
            ┌──────────────────────── ClusteringCoordinator ────────────────────────┐
            │  (application layer: knows where vectors live — SQLite / in-memory) │
            └───────────────┬─────────────────────────────────────────────────────┘
                            │ sampled score vectors (n, up to 16 features)
                            ▼
   ScheduleSampler ──▶ ScoreFeatureExtractor ──▶ FeatureNormalizer ──▶ AutoKSelector ──▶ ScikitLearnKMeansStrategy
   (≤ max_sample)      (scores → vector)         (min-max → [0,1])     (silhouette)       (sklearn primary; in-house fallback)
                            │                                                                     │
                            ▼                                                                     ▼
                     ClusterSummarizer  ◀────────────  ClusteringService (orchestrator)  ──▶  ClusterResult
                     (stats → sentence)                                                        (families + reps)
```

### Core Components

| Component | Role |
|---|---|
| `ClusterConfig` | The single contract describing one run: criteria, weights, K mode, sampling, seed. **This is the exact object the LLM layer produces.** |
| `ScoreFeatureExtractor` | Turns a schedule (or a bare score map) into a vector, in a fixed criterion order. |
| `FeatureNormalizer` | Min-max each dimension to `[0,1]` so no single score dominates the distance calculation. |
| `WeightedEuclideanDistanceMetric` | Calculates similarity in normalized space. The weights are what "group mostly by X" translates to. |
| `ScikitLearnKMeansStrategy` | **Primary** algorithm. Wraps scikit-learn's KMeans for performance and stability. |
| `KMeansClusteringStrategy` | **Fallback** algorithm. In-house k-means++ used when scikit-learn is not installed. |
| `AutoKSelector` | Picks K by mean **silhouette** score over a candidate range, evaluated on a capped sub-sample for speed. |
| `ScheduleSampler` | Draws a uniform representative sample (≤ `max_sample`) so the pipeline stays fast at scale. |
| `ClusterSummarizer` | Generates default, dependency-free one-line descriptions from simple statistics. |
| `ClusterResult` | Plain, picklable result models holding the formed families, their representative schedules, and population estimates. |
| `ClusteringService` | Orchestrates extract → normalize → choose-K → cluster → representatives → summarize. |
| `ClusteringCoordinator` | Application driver: samples IDs, reads score vectors from the repository, runs the service, and maps working positions back to global schedule IDs for drill-down. |

### Data Flow at Scale

1. **Sample** — `ScheduleSampler` draws up to `max_sample` (default 10,000) IDs from the population (`repository.count_scores()`).
2. **Read vectors** — `repository.read_score_vectors(criteria, ids)` pulls only the `schedule_scores` rows (no schedule materialized).
3. **Normalize** — Min-max scales features to `[0,1]`.
4. **Choose K** — Evaluates silhouette score over `[k_min, k_max]` on a capped subset (to keep O(n²) silhouette cheap).
5. **Cluster** — Runs k-means++ on the full working set with the chosen K.
6. **Representatives & Profiles** — Each family's archetype is the member nearest its centroid; per-cluster sizes are scaled back up to the full population.
7. **Summaries** — `ClusterSummarizer` turns each family's profile into a sentence.

**Drill-down:** `ClusteringRun.gidx_for(cluster.member_indices)` maps a family's member positions back to global schedule IDs. The existing `repository.get_raw_by_ids(...)` fetches them, and the existing sort mechanism still applies seamlessly because sorting a family simply means sorting that specific ID slice.

## 3. Free-Text Request Pipeline

The user can describe a grouping in plain language (English or Hebrew) via the cluster overview screen. The system translates this request into a `ClusterConfig`.

**Three-Layer Pipeline:**
1. **LLM**: If configured, an LLM extracts *intent topics* and weights.
2. **Keyword Parser**: If the LLM is off or fails, a fast offline parser scans for known keywords, emphasis cues, and requested group counts.
3. **Default**: If no match is found, falls back to automatic grouping using all core criteria.

**Supported Intent Topics:**
Requests map to 12 possible topics which control specific combinations of the 16 available criteria (5 base criteria + 11 extended features):
- `retake_time` (Moed gap)
- `study_prep` (Free days before mandatory)
- `daily_load` (Exams per day)
- `weekly_load` (Heavy weeks)
- `rest` (Spacing/breathing room)
- `consistency` (Even spacing)
- `consecutive` (Back-to-back mandatory)
- `span` (Compact vs spread out)
- `conflicts` (Elective clashes)
- `balance` (Even distribution)
- `general` (All criteria)
- `faculty_load` (Instructor/department load — time for instructors to grade and prepare, per-instructor and per-department)

*Thresholds & K Specification*: 
The pipeline respects numeric thresholds as emphasis boosts (e.g., "minimum 7 days" boosts retake weight). The number of clusters (K) can be explicitly requested using digits or words (e.g., "into 4 groups", "חמש קבוצות").

### Supported Criteria (16 Total)

The engine can cluster on any subset of 16 computed features (5 base criteria + 11 extended features).

**Base Sort Criteria:**
- `MIN_MANDATORY_GAP`: Min mandatory gap (days) — *More rest between mandatory exams*
- `AVG_ALL_COURSES_GAP`: Avg gap, all courses (days) — *More spread overall*
- `ELECTIVE_CONFLICTS`: Elective conflicts — *Fewer clashes (stored negated)*
- `MANDATORY_SPAN`: Mandatory span (days) — *Wider mandatory window*
- `MAX_EXAMS_PER_DAY`: Max exams per day — *Lighter busiest day (stored negated)*

**Extended Features:**
- `AVG_MOED_GAP`: Avg Moed A→B gap (days) — *More time to improve grade*
- `MIN_MOED_GAP`: Min Moed A→B gap (days) — *Best worst-case retake window*
- `GAP_STD_DEV`: Gap consistency — *More even spacing (stored negated)*
- `AVG_PREP_DAYS`: Avg prep days (mandatory) — *More free days before mandatory exams*
- `DOUBLE_EXAM_DAYS`: Double exam days — *Fewer days with 2+ exams (stored negated)*
- `BUSIEST_WEEK_COUNT`: Busiest week (exams) — *Lighter busiest week (stored negated)*
- `MAX_REST_DAYS`: Longest rest (days) — *Longer recovery window*
- `MANDATORY_CONSEC`: Consecutive mandatory days — *Fewer back-to-back mandatory pairs (stored negated)*
- `B2B_EXAM_INCIDENCE`: Back-to-back exam rate — *Lower percentage of back-to-back exams (stored negated)*
- `DEPT_EXAM_CONCURRENCY`: Dept exam concurrency — *Lower peak number of simultaneous department exams per day (stored negated)*
- `INSTRUCTOR_EXAM_GAP`: Min instructor gap — *Larger minimum gap between exams of the same instructor*

*(Note: "Stored negated" means the raw mathematical score is kept negative so that 'higher' mathematically always equates to 'better'. The UI automatically de-negates these for human-readable display.)*

## 4. Comparing Families (Compare View)

When users select two families to compare, the system presents a side-by-side breakdown of the archetypes to clarify the trade-offs between them.

**Delta Arrows:** 
The UI draws bold visual indicators (up/down arrows) highlighting which family performs better on a given metric. The direction of the arrow reflects the *preferred direction* of the metric (e.g., an Up arrow means a higher score is better, while a Down arrow means a lower score is better). Hovering over the arrows provides descriptive tooltips explaining the metric direction.

**5-Level Composite Ratings:**
Beyond raw numbers, the system abstracts combinations of metrics into high-level composite scores to help the user digest the data quickly. There are four composite categories, each driven by a distinct recipe of underlying metrics:
- **Student Comfort**: Considers minimum mandatory gaps, back-to-back exam rates, and average prep days.
- **Admin Load**: Considers elective conflicts and double-exam days.
- **Faculty Impact**: Considers department concurrency and instructor grading gaps.
- **Schedule Spread**: Considers the mandatory span window and maximum rest days.

**Dataset-Relative Normalization:**
To assign a human-readable rating (e.g., *Excellent, Good, Fair, Poor, Critical*), the system avoids static hardcoded thresholds. Instead, it uses **dynamic dataset-relative normalization**. 
The engine scans all cluster representatives in the active run, finding the minimum and maximum values for every metric. It maps each family's raw feature value to a percentage (0% to 100%) *relative to the available alternatives*. It then computes a weighted average of these normalized scores according to the composite recipes, producing highly distinct and accurate ratings that reflect how the families compare to the specific dataset at hand.

## 5. LLM Setup (Optional)

To enable the LLM for smarter free-text understanding, create a `.env` file in the project root. Without a key, the offline keyword parser is used.

```env
CLUSTER_LLM_API_KEY=your-key-here
CLUSTER_LLM_BASE_URL=https://api.groq.com/openai/v1
CLUSTER_LLM_MODEL=llama-3.3-70b-versatile
CLUSTER_LLM_TIMEOUT=15
```

**Recommended Free Providers:**
- **Groq**: Fast inference, generous free tier. (`https://api.groq.com/openai/v1` | model: `llama-3.3-70b-versatile`)
- **Google AI Studio**: Gemini models. (`https://generativelanguage.googleapis.com/v1beta/openai/` | model: `gemini-2.0-flash`)

*Note: The key is read from the environment only and is never stored in the repository.*
