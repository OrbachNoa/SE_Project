# Free-text clustering — setup & capabilities

The cluster overview screen lets you describe a grouping in plain language.
The app translates your request into a clustering configuration and runs it instantly —
no manual criterion selection required.

```
"group by the lightest exam days, into 4 groups"
"תקבץ בעיקר לפי פיזור המבחנים ל-3 קבוצות"
"לפחות 4 ימים בין כל מבחן, חמש קבוצות"
"I want schedules where mandatory exams don't stack up week after week"
```

The result is a `ClusterConfig` (which criteria to weight, and how many families).
A one-line summary below the text box shows exactly how your request was understood.
If the app cannot form as many families as you requested — because the data doesn't
vary enough on those dimensions — it tells you so.

---

## How it works (three-layer pipeline)

```
Your text
   │
   ▼
1. LLM  ──────────────────────► intent topics + optional threshold + k
   │  (if key is set and call succeeds)
   │  fails? ▼
2. Keyword parser ────────────► criteria + k   (always available, offline)
   │  nothing matched? ▼
3. Default ───────────────────► all 13 criteria, automatic K
```

**Layer 1 — LLM:** The model identifies one or more *intent topics* from a
closed list of 11 names (e.g. `retake_time`, `rest`, `balance`). Python maps
those topics to exact criterion IDs and weights — the model never has to
know the internal names. Failed calls (network error, 429 rate-limit) are
retried once with a 1.5-second back-off, then fall through silently.
Repeated identical requests are served from a 20-entry cache.

**Layer 2 — Keyword parser:** Scans for criterion-related words in English and
Hebrew, an emphasis cue ("mainly" / "בעיקר"), and a number of groups.
Handles digit and word-number K values ("4 groups", "ארבע קבוצות", "four families").
Always available, zero dependencies beyond the app itself.

**Layer 3 — Default:** Automatic grouping by all 13 criteria with K chosen
by silhouette score.

---

## Setup — optional LLM key

Without a key the keyword parser runs. To enable the LLM, create a `.env`
file in the project root (copy `.env.example` and fill in your key):

```
CLUSTER_LLM_API_KEY=your-key-here
CLUSTER_LLM_BASE_URL=https://api.groq.com/openai/v1
CLUSTER_LLM_MODEL=llama-3.3-70b-versatile
CLUSTER_LLM_TIMEOUT=20
```

| Variable | Required | Default | Notes |
|---|---|---|---|
| `CLUSTER_LLM_API_KEY` | yes (to enable LLM) | — | Without this the LLM stays off |
| `CLUSTER_LLM_BASE_URL` | no | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `CLUSTER_LLM_MODEL` | no | `gpt-4o-mini` | See recommended models below |
| `CLUSTER_LLM_TIMEOUT` | no | `20` | Seconds before timeout |

The key is read from the environment only — it is never stored in code or committed to the repo.
`.env` is in `.gitignore`. `.env.example` (no real key) is tracked and serves as a template.

### Recommended free providers

**Groq** (recommended) — fast inference, free tier, 1000 requests/day:
```bash
CLUSTER_LLM_BASE_URL=https://api.groq.com/openai/v1
CLUSTER_LLM_MODEL=llama-3.3-70b-versatile
```
Sign up at console.groq.com → API Keys → Create key.

**Google AI Studio** — 1500 requests/day:
```bash
CLUSTER_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
CLUSTER_LLM_MODEL=gemini-2.0-flash
```
Sign up at aistudio.google.com → Get API key.

Any other OpenAI-compatible provider (OpenAI, Together, Mistral, etc.) works
by pointing the two variables at it.

---

## Supported criteria — 13 total

The engine can cluster on any subset of these 13 scores.
The five *sort criteria* are always computed; the eight *extended features*
are computed at generation time and stored alongside them.

### Sort criteria (s_0 – s_4)

| ID | Label | Higher = |
|---|---|---|
| `MIN_MANDATORY_GAP` | Min mandatory gap (days) | More rest between mandatory exams |
| `AVG_ALL_COURSES_GAP` | Avg gap, all courses (days) | More spread overall |
| `ELECTIVE_CONFLICTS` | Elective conflicts | Fewer clashes (stored negated) |
| `MANDATORY_SPAN` | Mandatory span (days) | Wider mandatory window |
| `MAX_EXAMS_PER_DAY` | Max exams per day | Lighter busiest day (stored negated) |

### Extended features (f_0 – f_7)

| ID | Label | Higher = |
|---|---|---|
| `AVG_MOED_GAP` | Avg Moed A→B gap (days) | More time to improve grade |
| `MIN_MOED_GAP` | Min Moed A→B gap (days) | Best worst-case retake window |
| `GAP_STD_DEV` | Gap consistency | More even spacing (stored negated) |
| `AVG_PREP_DAYS` | Avg prep days (mandatory) | More free days before mandatory exams |
| `DOUBLE_EXAM_DAYS` | Double exam days | Fewer days with 2+ exams (stored negated) |
| `BUSIEST_WEEK_COUNT` | Busiest week (exams) | Lighter busiest week (stored negated) |
| `MAX_REST_DAYS` | Longest rest (days) | Longer recovery window |
| `MANDATORY_CONSEC` | Consecutive mandatory days | Fewer back-to-back mandatory pairs (stored negated) |

*"Stored negated"* means the raw score is negative so that higher always means better.
`CriterionDisplay` automatically de-negates values for display.

---

## Supported intent topics — 11 total

The LLM maps requests to one or more of these topics.
The keyword parser recognises the same topics from English and Hebrew keywords.

| Topic | Triggered by | Criteria used |
|---|---|---|
| `retake_time` | מועד ב, retake, fix grade, second chance | `AVG_MOED_GAP`, `MIN_MOED_GAP` |
| `study_prep` | זמן הכנה, prep time, free days before exam | `AVG_PREP_DAYS`, `MIN_MANDATORY_GAP` |
| `daily_load` | עומס ביום, exams per day, double exam | `MAX_EXAMS_PER_DAY`, `DOUBLE_EXAM_DAYS`, `BUSIEST_WEEK_COUNT` |
| `weekly_load` | שבוע עמוס, heavy week, weekly load | `BUSIEST_WEEK_COUNT`, `MAX_EXAMS_PER_DAY` |
| `rest` | מנוחה, רווח, spacing, breathing room | `MIN_MANDATORY_GAP`, `AVG_ALL_COURSES_GAP`, `MAX_REST_DAYS` |
| `consistency` | עקבי, אחיד, even spacing, consistent | `GAP_STD_DEV`, `AVG_ALL_COURSES_GAP` |
| `consecutive` | ימים רצופים, back-to-back, consecutive | `MANDATORY_CONSEC`, `MIN_MANDATORY_GAP` |
| `span` | מרוכז / מפוזר, compact / spread out | `MANDATORY_SPAN`, `AVG_ALL_COURSES_GAP` |
| `conflicts` | התנגשויות, elective clashes | `ELECTIVE_CONFLICTS`, `MAX_EXAMS_PER_DAY` |
| `balance` | מאוזן, שווה, even distribution | `BUSIEST_WEEK_COUNT`, `GAP_STD_DEV`, `AVG_ALL_COURSES_GAP` |
| `general` | vague or unrecognised request | all 13 criteria |

Multiple topics can be combined in one request — criteria are merged and weights boosted
for the primary topic (first topic × 1.0, second × 0.8, third+ × 0.6).

### Threshold support

Numeric bounds in the request boost the weight of the relevant criteria:

```
"לפחות 4 ימים בין מבחנים"  →  rest topic, weight × 1.8
"minimum 7 days between Moed A and B"  →  retake_time, weight × 2.4
"no more than 3 exams in a week"  →  weekly_load, threshold captured
```

Thresholds are emphasis hints, not hard filters. The engine clusters by similarity —
schedules that best satisfy the threshold will naturally group together.

### Negative phrasing

```
"לא רוצה שתי בחינות באותו יום"  →  daily_load
"I don't want back-to-back mandatory exams"  →  consecutive
"no heavy weeks"  →  weekly_load
```

### K specification

Both digit and word-number forms are recognised, in English and Hebrew:

```
"into 4 groups"     →  k = 4
"ארבע קבוצות"      →  k = 4
"four families"     →  k = 4
"לחמש קבוצות"      →  k = 5   (Hebrew prepositional prefix handled)
```

Numbers that describe a characteristic — "7 days", "3 exams" — are never
mistaken for K.

---

## Fuzzy matching

The LLM occasionally outputs topic names that are close but not exact
(e.g. `"load"` instead of `"daily_load"`). A 28-entry alias map normalises
these before lookup:

```
"load" → daily_load    "gap" → rest         "moed" → retake_time
"prep" → study_prep    "even" → balance     "compact" → span
"study" → study_prep   "gaps" → rest        "back2back" → consecutive
```

Unknown topics that survive fuzzy matching are skipped silently; the remaining
matched topics still drive the result.

---

## What the card shows

Each family card displays only the criteria that were actually used for
clustering — not a fixed list of five. A retake-time request shows two rows;
a general request shows all thirteen. Values are de-negated and labelled
using `CriterionDisplay` so they are always human-readable.

---

## Caveats

**Data flatness:** Some criteria have very little variation across schedules
(e.g. all schedules may have `MAX_EXAMS_PER_DAY = 2`). Clustering on a flat
criterion produces fewer meaningful families than requested. The app detects
this and displays a notice: *"Note: only X families could be formed — the
data may not vary enough on these criteria."*

**Rate limits:** Free-tier providers cap at ~1000 requests/day. The app
retries once on HTTP 429 (1.5 s back-off) and caches the last 20 results,
so repeated identical requests never cost an API call.

**No key:** Without `CLUSTER_LLM_API_KEY`, the keyword parser runs instead.
It is less flexible on novel phrasings but covers the most common requests
correctly and works entirely offline.