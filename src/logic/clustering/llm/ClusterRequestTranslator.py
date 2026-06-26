"""Translate a free-text clustering request into a validated ClusterConfig.

Order of attempts (each one degrades gracefully to the next):
  1. LLM — if a client is configured, ask it to identify intent topics, then
     map those topics to criteria in Python (the LLM never sees criterion IDs).
  2. Keyword parser — always available, no dependency, English + Hebrew.
  3. Default — automatic grouping by all criteria.

The result is always a valid ``ClusterConfig`` plus a short, human-readable
interpretation of what the request was understood to mean, so the UI can show the
user how their words were applied. ``validate_config`` is simply
``ClusterConfig.__post_init__`` / ``.validate()``.
"""
from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO, K_MODE_FIXED
from src.logic.clustering.ExtendedFeatureComputer import (
    AVG_MOED_GAP, MIN_MOED_GAP, GAP_STD_DEV, AVG_PREP_DAYS,
    DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT, MAX_REST_DAYS, MANDATORY_CONSEC,
    B2B_EXAM_INCIDENCE, DEPT_EXAM_CONCURRENCY, INSTRUCTOR_EXAM_GAP, ALL_EXTENDED_FEATURES,
)
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.comparators.ScheduleScorer import (
    MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, ELECTIVE_CONFLICTS,
    MANDATORY_SPAN, MAX_EXAMS_PER_DAY, ALL_CRITERIA,
)

_SYSTEM_PROMPT = """You identify the clustering intent in a student's exam schedule request.

Choose from these topics ONLY (use exact names):
- "retake_time"   : user wants more time between Moed A and Moed B (retake gap)
- "study_prep"    : user wants more free days to study before mandatory exams
- "daily_load"    : user wants fewer exams on the same day
- "weekly_load"   : user wants lighter weeks overall
- "rest"          : user wants more rest/spacing between exams generally
- "consistency"   : user wants evenly spaced exams (consistent gaps)
- "consecutive"   : user wants to avoid back-to-back mandatory exam days
- "span"          : user wants to control how concentrated or spread out mandatory exams are — compact or wide window
- "conflicts"     : user wants fewer elective exam clashes
- "balance"       : user wants an even, balanced distribution of exams
                    across the period — equal weeks, no overloaded periods
- "general"       : general or unclear request — use all criteria

When the request contains multiple conditions joined by AND / ו / גם / and also,
identify a separate topic for EACH condition.
Exception: if both conditions map to the same topic, merge them into one topic with the higher threshold.

Output ONLY valid JSON, no prose, no code fences, no <think> tags:
{
  "topics": [<one or more topic names from the list above>],
  "thresholds": {"<topic>": <number>},
  "directions": {"span": "compact" | "spread"},
  "k_mode": "auto" | "fixed",
  "k": <integer 2-20, only when k_mode is "fixed">,
  "explanation": "<one sentence in the same language as the request>"
}
"thresholds" is optional — omit it entirely when no numeric bound is mentioned.
"directions" is optional — omit it entirely unless the span topic is present and direction is clear.

IMPORTANT RULES:
- The request may be written casually, formally, or as a system description.
  Treat all of them as the student's intent.
  "user wants X" and "give me X" and "תקבץ לפי X" all mean the same thing.
- Any mention of Moed A, Moed B, מועד א, מועד ב, retake, fix grade, improve score,
  second chance → ALWAYS use ["retake_time"]. Never map this to "general".
- Use "general" ONLY when the request is completely unrelated to exam scheduling
  or contains no recognizable intent (e.g. "!@#$%", "hello", "תן לי לוחות טובים").
  When in doubt, pick the closest topic — do NOT default to "general".
- The value for 'k' must come ONLY from explicit grouping phrases:
  'into X groups', 'X families', 'X קבוצות', 'divided into X', 'X clusters'.
  Numbers that describe characteristics (e.g. '7 days', '3 exams', '14 days apart')
  are NOT the number of groups — ignore them when setting k.
- Word numbers ("four", "ארבע", "חמש", "three", "שלוש") adjacent to group words
  ("groups", "families", "קבוצות", "משפחות") ARE valid k values — treat them as digits.
- When the request contains a number describing a minimum or maximum
  (e.g. 'at least 4 days', 'no more than 2 exams', 'minimum 7 days'),
  extract it as a threshold for the relevant topic.
  Thresholds are hints for emphasis — not hard filters.
- Negative phrasing ('I don't want X', 'לא רוצה X', 'no X', 'בלי X') means
  the user wants to MINIMIZE X — map to the relevant topic with high weight.
- 'מרוכז'/'compact'/'concentrated' → span topic, compact direction.
  'מפוזר'/'spread out'/'distributed'/'פזור' → span topic, wide direction.
- When span direction matters, add:
  "directions": {"span": "compact"} for concentrated/מרוכז requests,
  "directions": {"span": "spread"} for spread-out/מפוזר requests.
- For load requests: prefer "daily_load" when the user mentions per-day load,
  prefer "weekly_load" when the user mentions per-week load.
  Use both when the request is general about load.

Examples:

Request: "תקבץ לי לפי לוחות שנותנים הכי הרבה זמן לתקן מבחן"
Output: {"topics": ["retake_time"], "k_mode": "auto", "explanation": "קיבוץ לפי זמן בין מועד א׳ למועד ב׳"}

Request: "group by exam load, into 3 groups"
Output: {"topics": ["daily_load", "weekly_load"], "k_mode": "fixed", "k": 3, "explanation": "Grouping by exam load, 3 families"}

Request: "אני רוצה קבוצות שנותנות זמן הכנה טוב לפני כל מבחן חובה"
Output: {"topics": ["study_prep"], "k_mode": "auto", "explanation": "קיבוץ לפי זמן הכנה לפני מבחנות חובה"}

Request: "תן לי 5 קבוצות לפי כל הקריטריונים"
Output: {"topics": ["general"], "k_mode": "fixed", "k": 5, "explanation": "5 קבוצות לפי כל הקריטריונים"}

Request: "I want no back-to-back mandatory exams"
Output: {"topics": ["consecutive", "rest"], "k_mode": "auto", "explanation": "Grouping by consecutive mandatory exam days"}

Request: "I want schedules with good preparation time before mandatory exams and easy days"
Output: {"topics": ["study_prep", "daily_load"], "k_mode": "auto", "explanation": "Grouping by preparation time and daily exam load"}

Request: "תקבץ לפי לוחות שבהם הבחינות מפוזרות בצורה אחידה"
Output: {"topics": ["consistency"], "k_mode": "auto", "explanation": "קיבוץ לפי אחידות הרווחים בין בחינות"}

Request: "I want schedules where mandatory exams don't stack up week after week"
Output: {"topics": ["weekly_load", "consecutive"], "k_mode": "auto", "explanation": "Grouping by weekly exam load and consecutive mandatory days"}

Request: "group by how spread out the mandatory exams are across the semester"
Output: {"topics": ["span"], "k_mode": "auto", "explanation": "Grouping by mandatory exam span across the period"}

Request: "אני רוצה שיהיו כמה שפחות התנגשויות בין קורסי בחירה"
Output: {"topics": ["conflicts"], "k_mode": "auto", "explanation": "קיבוץ לפי מספר ההתנגשויות בין קורסי בחירה"}

Request: "תן לי 3 קבוצות שלא יהיו ימים רצופים עם בחינות חובה"
Output: {"topics": ["consecutive", "rest"], "k_mode": "fixed", "k": 3, "explanation": "3 קבוצות לפי ימים רצופים עם בחינות חובה"}

Request: "I want lighter weeks with fewer exams per day, into 4 groups"
Output: {"topics": ["weekly_load", "daily_load"], "k_mode": "fixed", "k": 4, "explanation": "Grouping by weekly and daily exam load, 4 families"}

Request: "give me schedules with more time between Moed A and Moed B retake"
Output: {"topics": ["retake_time"], "k_mode": "auto", "explanation": "Grouping by time between Moed A and Moed B"}

Request: "לא רוצה שתי בחינות באותו יום"
Output: {"topics": ["daily_load"], "k_mode": "auto", "explanation": "קיבוץ לפי ימים עם שתי בחינות או יותר"}

Request: "לפחות 4 ימים בין כל מבחן"
Output: {"topics": ["rest"], "thresholds": {"rest": 4}, "k_mode": "auto", "explanation": "קיבוץ לפי רווח בין בחינות, לפחות 4 ימים"}

Request: "שיהיה לי זמן לנשום בין הבחינות"
Output: {"topics": ["rest", "consistency"], "k_mode": "auto", "explanation": "קיבוץ לפי מרחק ועקביות הרווחים בין בחינות"}

Request: "I want schedules where exams are concentrated early in the period"
Output: {"topics": ["span"], "k_mode": "auto", "explanation": "Grouping by exam concentration at start of period"}

Request: "minimum 7 days between Moed A and Moed B, into 3 groups"
Output: {"topics": ["retake_time"], "thresholds": {"retake_time": 7}, "k_mode": "fixed", "k": 3, "explanation": "Grouping by retake gap, minimum 7 days, 3 families"}

Request: "שלא יהיה שבוע עם יותר מ-3 בחינות"
Output: {"topics": ["weekly_load"], "thresholds": {"weekly_load": 3}, "k_mode": "auto", "explanation": "קיבוץ לפי עומס שבועי, לא יותר מ-3 בחינות בשבוע"}

Request: "I want free time before my mandatory exams, at least 5 days"
Output: {"topics": ["study_prep"], "thresholds": {"study_prep": 5}, "k_mode": "auto", "explanation": "Grouping by preparation time before mandatory exams"}

Request: "תן לי מבחנים עם לפחות יומיים הפרש בארבע קבוצות"
Output: {"topics": ["rest"], "thresholds": {"rest": 2}, "k_mode": "fixed", "k": 4, "explanation": "קיבוץ לפי רווח בין בחינות, לפחות יומיים, ארבע קבוצות"}

Request: "לא רוצה ימים רצופים עם בחינות חובה"
Output: {"topics": ["consecutive"], "k_mode": "auto", "explanation": "קיבוץ לפי ימים רצופים עם בחינות חובה"}

Request: "תן לי לוחות טובים"
Output: {"topics": ["general"], "k_mode": "auto", "explanation": "קיבוץ לפי כל הקריטריונים"}

Request: "three groups by retake time"
Output: {"topics": ["retake_time"], "k_mode": "fixed", "k": 3, "explanation": "Grouping by retake time, 3 families"}

Request: "אני רוצה שהבחינות יהיו מרוכזות בתחילת התקופה"
Output: {"topics": ["span"], "directions": {"span": "compact"}, "k_mode": "auto", "explanation": "קיבוץ לפי ריכוז בחינות בתחילת התקופה"}

Request: "I want exams spread out across the full semester"
Output: {"topics": ["span"], "directions": {"span": "spread"}, "k_mode": "auto", "explanation": "Grouping by exam spread across the semester"}

Request: "תן לי קבוצות עם החלונות הכי טובים בין הבחינות"
Output: {"topics": ["rest"], "k_mode": "auto", "explanation": "קיבוץ לפי רווח המנוחה בין בחינות"}

Request: "תן לי קבוצות עם חלון הכנה טוב לפני כל בחינת חובה"
Output: {"topics": ["study_prep"], "k_mode": "auto", "explanation": "קיבוץ לפי זמן הכנה לפני בחינות חובה"}

Request: "אני רוצה שכל השבועות שווים"
Output: {"topics": ["balance"], "k_mode": "auto", "explanation": "קיבוץ לפי איזון עומס הבחינות לאורך התקופה"}

Request: "give me a balanced schedule with even exam distribution"
Output: {"topics": ["balance"], "k_mode": "auto", "explanation": "Grouping by balanced exam distribution"}"""

_USER_TEMPLATE = "Request:\n{request}\n\nReturn the JSON configuration."

_TOPIC_CRITERIA: Dict[str, Tuple[list, dict]] = {
    "retake_time":  ([AVG_MOED_GAP, MIN_MOED_GAP], {AVG_MOED_GAP: 2.0}),
    "study_prep":   ([AVG_PREP_DAYS, MIN_MANDATORY_GAP], {AVG_PREP_DAYS: 3.0}),
    "daily_load":   ([MAX_EXAMS_PER_DAY, DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT], {MAX_EXAMS_PER_DAY: 2.0}),
    "weekly_load":  ([BUSIEST_WEEK_COUNT, MAX_EXAMS_PER_DAY], {BUSIEST_WEEK_COUNT: 2.0}),
    "rest":         ([MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, MAX_REST_DAYS], {}),
    "consistency":  ([GAP_STD_DEV, AVG_ALL_COURSES_GAP], {GAP_STD_DEV: 2.0}),
    "consecutive":  ([B2B_EXAM_INCIDENCE, MANDATORY_CONSEC, MIN_MANDATORY_GAP], {MANDATORY_CONSEC: 3.0}, {B2B_EXAM_INCIDENCE: 3.0}),
    "span":         ([MANDATORY_SPAN, AVG_ALL_COURSES_GAP], {}),
    "conflicts":    ([ELECTIVE_CONFLICTS, MAX_EXAMS_PER_DAY], {}),
    "balance":      ([BUSIEST_WEEK_COUNT, GAP_STD_DEV, AVG_ALL_COURSES_GAP],
                     {BUSIEST_WEEK_COUNT: 1.5, GAP_STD_DEV: 1.5}),
    "general":      (list(ALL_CRITERIA) + list(ALL_EXTENDED_FEATURES), {}),
}

_FUZZY_TOPIC_MAP: Dict[str, str] = {
    "load":             "daily_load",
    "daily":            "daily_load",
    "cramming":         "daily_load",
    "cramped":          "daily_load",
    "weekly":           "weekly_load",
    "heavy":            "weekly_load",
    "light":            "weekly_load",
    "retake":           "retake_time",
    "retake_gap":       "retake_time",
    "moed":             "retake_time",
    "prep":             "study_prep",
    "preparation":      "study_prep",
    "study":            "study_prep",
    "revision":         "study_prep",
    "gap":              "rest",
    "gaps":             "rest",
    "rest_time":        "rest",
    "spacing":          "consistency",
    "spread":           "span",
    "compact":          "span",
    "concentrated":     "span",
    "distribution":     "balance",
    "even":             "balance",
    "balanced":         "balance",
    "uniform":          "balance",
    "back_to_back":     "consecutive",
    "backtoback":       "consecutive",
    "back2back":        "consecutive",
    "consecutive_days": "consecutive",
}


@dataclass(slots=True)
class TranslationResult:
    """A finished translation: the config, a human summary, and its source."""

    config: ClusterConfig
    interpretation: str
    source: str  # "llm" | "heuristic" | "default"


class ClusterRequestTranslator:
    """Free-text → ClusterConfig, LLM-first with a keyword fallback."""

    def __init__(
        self,
        llm_client: Optional[ILLMClient] = None,
        parser: Optional[HeuristicRequestParser] = None,
    ) -> None:
        self._llm = llm_client
        self._parser = parser or HeuristicRequestParser()
        self._cache: dict = {}

    def translate(self, text: str) -> TranslationResult:
        request = (text or "").strip()
        if not request:
            return TranslationResult(
                ClusterConfig.default(), "Automatic grouping by all criteria.", "default"
            )

        if request in self._cache:
            return self._cache[request]

        # 1. LLM, when configured.
        if self._llm is not None and self._llm.is_available():
            try:
                raw = self._llm.complete(_SYSTEM_PROMPT, _USER_TEMPLATE.format(request=request))
                config, interpretation = self._config_from_llm(raw)
                config.validate()
                result = TranslationResult(config, interpretation, "llm")
                # DEBUG
                print(f"[LLM OK] k={config.k_mode}:{config.k} | criteria={config.criteria[:2]}... | '{request[:40]}'")
                if len(self._cache) >= 20:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[request] = result
                return result
            except Exception as exc:
                warnings.warn(
                    f"LLM clustering request failed: {exc}", RuntimeWarning, stacklevel=2
                )  # fall through to the keyword parser

        # 2. Keyword parser (always available).
        config, interpretation = self._parser.parse(request)
        result = TranslationResult(config, interpretation, "heuristic")
        if len(self._cache) >= 20:
            self._cache.pop(next(iter(self._cache)))
        self._cache[request] = result
        return result

    # ── LLM JSON handling ────────────────────────────────────────────────────

    def _config_from_llm(self, raw: str) -> Tuple[ClusterConfig, str]:
        print(raw)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        data = self._extract_json(raw)

        raw_topics = data.get("topics") or ["general"]
        topics = []
        for t in raw_topics:
            normalized = _FUZZY_TOPIC_MAP.get(t, t)
            if normalized not in _TOPIC_CRITERIA:
                continue
            topics.append(normalized)
        thresholds: dict = data.get("thresholds") or {}

        merged_criteria: list = []
        merged_weights: dict = {}
        _DECAY = [1.0, 0.8, 0.6]
        for rank, topic in enumerate(topics):
            decay = _DECAY[min(rank, len(_DECAY) - 1)]
            crit, weights = _TOPIC_CRITERIA[topic]
            for c in crit:
                if c not in merged_criteria:
                    merged_criteria.append(c)
            for k, v in weights.items():
                merged_weights[k] = max(merged_weights.get(k, 1.0), v * decay)

        # Apply threshold-based weight boosts: threshold N → multiplier (1 + N/5).
        for topic, threshold in thresholds.items():
            normalized_t = _FUZZY_TOPIC_MAP.get(topic, topic)
            if normalized_t in _TOPIC_CRITERIA:
                crit, _ = _TOPIC_CRITERIA[normalized_t]
                multiplier = 1.0 + float(threshold) / 5.0
                for c in crit:
                    base = merged_weights.get(c, 1.0)
                    merged_weights[c] = min(base * multiplier, 5.0)

        # Apply span direction: compact → de-emphasize MANDATORY_SPAN (0.5),
        # spread → emphasize (2.0).
        directions: dict = data.get("directions") or {}
        span_dir = directions.get("span")
        if span_dir == "compact":
            merged_weights[MANDATORY_SPAN] = 0.5
        elif span_dir == "spread":
            merged_weights[MANDATORY_SPAN] = 2.0

        if not merged_criteria:
            merged_criteria = list(ALL_CRITERIA) + list(ALL_EXTENDED_FEATURES)

        kwargs: dict = {"criteria": tuple(merged_criteria)}
        if merged_weights:
            kwargs["weights"] = merged_weights

        k_mode = data.get("k_mode", "auto")
        if k_mode == K_MODE_FIXED:
            raw_k = data.get("k")
            if raw_k is not None:
                kwargs["k_mode"] = K_MODE_FIXED
                kwargs["k"] = max(2, min(int(raw_k), 20))
            else:
                kwargs["k_mode"] = K_MODE_AUTO
        else:
            kwargs["k_mode"] = K_MODE_AUTO

        config = ClusterConfig(**kwargs)
        interpretation = (data.get("explanation") or "").strip() or "Custom grouping applied."
        return config, interpretation

    @staticmethod
    def _extract_json(raw: str) -> Dict:
        """Pull the first JSON object out of the model's reply."""
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise ValueError("no JSON object found in LLM reply")
        return json.loads(match.group(0))
