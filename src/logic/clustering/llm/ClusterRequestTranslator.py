"""Translate a free-text clustering request into a validated ClusterConfig.

Order of attempts (each one degrades gracefully to the next):
  1. LLM — if a client is configured, ask it to identify intent topics, then
     map those topics to criteria in Python (the LLM never sees criterion IDs).
  2. Keyword parser — always available, no dependency, English + Hebrew.
  3. Default — application default grouping over the core criteria.

The result is always a valid ``ClusterConfig`` plus a short, human-readable
interpretation of what the request was understood to mean, so the UI can show the
user how their words were applied. ``validate_config`` is simply
``ClusterConfig.__post_init__`` / ``.validate()``.
"""
from __future__ import annotations

import json
import logging
import re
import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

_log = logging.getLogger(__name__)

from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO, K_MODE_FIXED
from src.logic.clustering.ExtendedFeatureComputer import ALL_EXTENDED_FEATURES
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.clustering.llm.ClusterTopicMetadata import (
    FUZZY_TOPIC_MAP,
    SMART_K,
    TOPIC_CRITERIA,
)
from src.logic.comparators.ScheduleScorer import MANDATORY_SPAN, ALL_CRITERIA

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
- "faculty_load"  : user wants enough time between exams for instructors
                    to grade and prepare — considers per-instructor and per-department load
- "general"       : general or unclear request — use all criteria

When the request contains multiple conditions joined by AND / ו / גם / and also,
identify a separate topic for EACH condition.
Exception: if both conditions map to the same topic, merge them into one topic with the higher threshold.

Output ONLY valid JSON, no prose, no code fences, no <think> tags:
{
  "topics": [<one or more topic names from the list above>],
  "thresholds": {"<topic>": <number>},
  "confidence": {"<topic>": <float 0.0-1.0>},   // optional
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
- Include 'confidence' scores (0.0–1.0) for each topic when you are not
  fully certain. High confidence (>0.8) = clear match.
  Low confidence (<0.5) = weak signal. Omit 'confidence' entirely when
  all topics are clearly matched (saves tokens).

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
Output: {"topics": ["balance"], "k_mode": "auto", "explanation": "Grouping by balanced exam distribution"}

Request: "give instructors enough time between their exams"
Output: {"topics": ["faculty_load"], "k_mode": "auto", "explanation": "Grouping by instructor and department exam load"}

Request: "שיהיה למרצים זמן לבדוק בין מבחן למבחן"
Output: {"topics": ["faculty_load"], "k_mode": "auto", "explanation": "קיבוץ לפי עומס המרצים בין הבחינות"}

Request: "אני רוצה לוחות שנוחים ומאוזנים"
Output: {"topics": ["rest", "balance"],
         "confidence": {"rest": 0.7, "balance": 0.6},
         "k_mode": "auto",
         "explanation": "קיבוץ לפי מנוחה ואיזון עומס"}"""

_USER_TEMPLATE = "Request:\n{request}\n\nReturn the JSON configuration."

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
                ClusterConfig.default(), "Default grouping by core schedule quality, 4 families.", "default"
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
                _log.debug("[LLM OK] k=%s:%s | criteria=%s... | '%s'",
                           config.k_mode, config.k, config.criteria[:2], request[:40])
                if len(self._cache) >= 20:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[request] = result
                return result
            except Exception as exc:
                warnings.warn(
                    f"LLM clustering request failed: {exc}", RuntimeWarning, stacklevel=2
                )  # fall through to the keyword parser

        # 2. Keyword parser (always available).
        # Not cached — a transient LLM failure must not permanently block LLM for this text.
        config, interpretation = self._parser.parse(request)
        return TranslationResult(config, interpretation, "heuristic")

    # ── LLM JSON handling ────────────────────────────────────────────────────

    def _config_from_llm(self, raw: str) -> Tuple[ClusterConfig, str]:
        _log.debug("[LLM raw] %s", raw)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        data = self._extract_json(raw)

        topics = self._normalized_topics(data.get("topics") or ["general"])
        thresholds: dict = data.get("thresholds") or {}
        confidence_map = data.get("confidence") or {}

        merged_criteria, merged_weights = self._merge_topic_criteria(
            topics, confidence_map
        )

        # Apply threshold-based weight boosts: threshold N → multiplier (1 + N/5).
        self._apply_threshold_weight_boosts(merged_weights, thresholds)

        # Apply span direction: compact → de-emphasize MANDATORY_SPAN (0.5),
        # spread → emphasize (2.0).
        self._apply_span_direction(merged_weights, data.get("directions") or {})

        if not merged_criteria:
            merged_criteria = list(ALL_CRITERIA) + list(ALL_EXTENDED_FEATURES)

        kwargs: dict = {"criteria": tuple(merged_criteria)}
        if merged_weights:
            kwargs["weights"] = merged_weights

        kwargs.update(self._k_kwargs(data))
        self._apply_smart_k(kwargs, topics)

        config = ClusterConfig(**kwargs)
        interpretation = (data.get("explanation") or "").strip() or "Custom grouping applied."
        return config, interpretation

    def _normalized_topics(self, raw_topics: list) -> list:
        """Normalize model topic names and drop unknown values."""
        topics = []
        for topic in raw_topics:
            normalized = FUZZY_TOPIC_MAP.get(topic, topic)
            if normalized in TOPIC_CRITERIA:
                topics.append(normalized)
        return topics

    def _merge_topic_criteria(self, topics: list, confidence_map: dict) -> Tuple[list, dict]:
        """Merge topic criteria and base weights, preserving topic order."""
        merged_criteria: list = []
        merged_weights: dict = {}
        decay = [1.0, 0.8, 0.6]
        for rank, topic in enumerate(topics):
            criteria, weights = TOPIC_CRITERIA[topic]
            confidence = confidence_map.get(topic, 1.0)
            confidence = max(0.1, min(1.0, float(confidence)))
            effective_multiplier = decay[min(rank, len(decay) - 1)] * confidence
            for criterion in criteria:
                if criterion not in merged_criteria:
                    merged_criteria.append(criterion)
            for criterion, weight in weights.items():
                scaled = weight * effective_multiplier
                merged_weights[criterion] = max(merged_weights.get(criterion, 0.0), scaled)
        return merged_criteria, merged_weights

    def _apply_threshold_weight_boosts(self, weights: dict, thresholds: dict) -> None:
        """Apply threshold-based emphasis boosts in-place."""
        for topic, threshold in thresholds.items():
            normalized = FUZZY_TOPIC_MAP.get(topic, topic)
            if normalized not in TOPIC_CRITERIA:
                continue
            criteria, _ = TOPIC_CRITERIA[normalized]
            multiplier = 1.0 + float(threshold) / 5.0
            for criterion in criteria:
                base = weights.get(criterion, 1.0)
                weights[criterion] = min(base * multiplier, 5.0)

    def _apply_span_direction(self, weights: dict, directions: dict) -> None:
        """Apply the special compact/spread span direction weight."""
        span_dir = directions.get("span")
        if span_dir == "compact":
            weights[MANDATORY_SPAN] = 0.5
        elif span_dir == "spread":
            weights[MANDATORY_SPAN] = 2.0

    def _k_kwargs(self, data: dict) -> dict:
        """Build explicit K settings from the LLM payload."""
        if data.get("k_mode", "auto") != K_MODE_FIXED:
            return {"k_mode": K_MODE_AUTO}
        raw_k = data.get("k")
        if raw_k is None:
            return {"k_mode": K_MODE_AUTO}
        return {
            "k_mode": K_MODE_FIXED,
            "k": max(2, min(int(raw_k), 20)),
        }

    def _apply_smart_k(self, kwargs: dict, topics: list) -> None:
        """Fill in topic-specific K only when the user did not set K explicitly."""
        if kwargs.get("k_mode") != K_MODE_AUTO or not topics:
            return
        suggested_k = SMART_K.get(topics[0])
        if suggested_k is not None:
            kwargs["k_mode"] = K_MODE_FIXED
            kwargs["k"] = suggested_k

    @staticmethod
    def _extract_json(raw: str) -> Dict:
        """Pull the first JSON object out of the model's reply."""
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise ValueError("no JSON object found in LLM reply")
        return json.loads(match.group(0))
