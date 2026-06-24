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
    ALL_EXTENDED_FEATURES,
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
- "span"          : user wants mandatory exams spread over a wide window
- "conflicts"     : user wants fewer elective exam clashes
- "general"       : general or unclear request — use all criteria

When the request contains multiple conditions joined by AND / ו / גם / and also,
identify a separate topic for EACH condition.

Output ONLY valid JSON, no prose, no code fences, no <think> tags:
{
  "topics": [<one or more topic names from the list above>],
  "k_mode": "auto" | "fixed",
  "k": <integer 2-20, only when k_mode is "fixed">,
  "explanation": "<one sentence in the same language as the request>"
}

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
Output: {"topics": ["study_prep", "daily_load"], "k_mode": "auto", "explanation": "Grouping by preparation time and daily exam load"}"""

_USER_TEMPLATE = "Request:\n{request}\n\nReturn the JSON configuration."

_TOPIC_CRITERIA: Dict[str, Tuple[list, dict]] = {
    "retake_time":  ([AVG_MOED_GAP, MIN_MOED_GAP], {AVG_MOED_GAP: 2.0}),
    "study_prep":   ([AVG_PREP_DAYS, MIN_MANDATORY_GAP], {AVG_PREP_DAYS: 3.0}),
    "daily_load":   ([MAX_EXAMS_PER_DAY, DOUBLE_EXAM_DAYS, BUSIEST_WEEK_COUNT], {MAX_EXAMS_PER_DAY: 2.0}),
    "weekly_load":  ([BUSIEST_WEEK_COUNT, MAX_EXAMS_PER_DAY], {BUSIEST_WEEK_COUNT: 2.0}),
    "rest":         ([MIN_MANDATORY_GAP, AVG_ALL_COURSES_GAP, MAX_REST_DAYS], {}),
    "consistency":  ([GAP_STD_DEV, AVG_ALL_COURSES_GAP], {GAP_STD_DEV: 2.0}),
    "consecutive":  ([MANDATORY_CONSEC, MIN_MANDATORY_GAP], {MANDATORY_CONSEC: 3.0}),
    "span":         ([MANDATORY_SPAN, AVG_ALL_COURSES_GAP], {}),
    "conflicts":    ([ELECTIVE_CONFLICTS, MAX_EXAMS_PER_DAY], {}),
    "general":      (list(ALL_CRITERIA) + list(ALL_EXTENDED_FEATURES), {}),
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

    def translate(self, text: str) -> TranslationResult:
        request = (text or "").strip()
        if not request:
            return TranslationResult(
                ClusterConfig.default(), "Automatic grouping by all criteria.", "default"
            )

        # 1. LLM, when configured.
        if self._llm is not None and self._llm.is_available():
            try:
                raw = self._llm.complete(_SYSTEM_PROMPT, _USER_TEMPLATE.format(request=request))
                config, interpretation = self._config_from_llm(raw)
                config.validate()
                return TranslationResult(config, interpretation, "llm")
            except Exception as exc:
                warnings.warn(
                    f"LLM clustering request failed: {exc}", RuntimeWarning, stacklevel=2
                )  # fall through to the keyword parser

        # 2. Keyword parser (always available).
        config, interpretation = self._parser.parse(request)
        return TranslationResult(config, interpretation, "heuristic")

    # ── LLM JSON handling ────────────────────────────────────────────────────

    def _config_from_llm(self, raw: str) -> Tuple[ClusterConfig, str]:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        data = self._extract_json(raw)

        topics = data.get("topics") or ["general"]

        merged_criteria: list = []
        merged_weights: dict = {}
        for topic in topics:
            if topic in _TOPIC_CRITERIA:
                crit, weights = _TOPIC_CRITERIA[topic]
                for c in crit:
                    if c not in merged_criteria:
                        merged_criteria.append(c)
                for k, v in weights.items():
                    merged_weights[k] = max(merged_weights.get(k, 1.0), v)

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
