# Free-text clustering — setup

The cluster overview has a **"Describe a grouping"** text box. You type a request
in plain language (English or Hebrew) and the app turns it into a clustering
configuration and runs it.

Examples:
- "group by the lightest exam days, into 4 groups"
- "תקבץ בעיקר לפי פיזור המבחנים ל-3 קבוצות"
- "compact schedules, few exams per day"

## Works out of the box — no key required

With **no setup at all**, the request is parsed by a built-in keyword parser
(English + Hebrew). It recognises the five criteria, an emphasis word
("mainly" / "בעיקר"), and a number of groups, and falls back to automatic
grouping for anything it can't map. This path is free and offline.

## Optional: use a real LLM

For smarter understanding of free text, point the app at any **OpenAI-compatible**
chat API via environment variables. If a key is present it is used; if the call
fails for any reason, the app silently falls back to the keyword parser.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CLUSTER_LLM_API_KEY` | yes (to enable) | — | API key; without it the LLM stays off |
| `CLUSTER_LLM_BASE_URL` | no | `https://api.openai.com/v1` | provider endpoint |
| `CLUSTER_LLM_MODEL` | no | `gpt-4o-mini` | model name |
| `CLUSTER_LLM_TIMEOUT` | no | `20` | request timeout (seconds) |

The key is read from the environment only — it is never stored in the code or repo.

### Example: a free provider (Groq)

Groq exposes an OpenAI-compatible endpoint with a free tier. With a free Groq key:

```bash
# Windows (PowerShell)
setx CLUSTER_LLM_API_KEY  "your-groq-key"
setx CLUSTER_LLM_BASE_URL "https://api.groq.com/openai/v1"
setx CLUSTER_LLM_MODEL    "llama-3.3-70b-versatile"
```

(Any other OpenAI-compatible provider works the same way — just change the three
values. To go back to keyword-only, unset `CLUSTER_LLM_API_KEY`.)

## How it maps to the engine

The request becomes a `ClusterConfig` (which criteria to use, optional per-criterion
weights, and the number of families). That is the exact same config the automatic
path uses, so the engine itself is unchanged — the text box only fills it in. The
overview shows a one-line summary of how your request was understood.
