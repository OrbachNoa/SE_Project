"""Dependency-free keyword parser: free-text request → ClusterConfig.

This is the always-available fallback used when no LLM is configured (or the call
fails). It scans the request for words that map to the five score criteria, an
emphasis cue ("mainly", "בעיקר"), and a requested number of groups, in English or
Hebrew. It is intentionally simple and conservative: anything it cannot map falls
back to sensible defaults (all criteria, automatic K), so it never errors.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO, K_MODE_FIXED
from src.logic.clustering import CriterionDisplay
from src.logic.comparators.ScheduleScorer import (
    AVG_ALL_COURSES_GAP,
    ELECTIVE_CONFLICTS,
    MANDATORY_SPAN,
    MAX_EXAMS_PER_DAY,
    MIN_MANDATORY_GAP,
)
from src.logic.clustering.ExtendedFeatureComputer import (
    GAP_STD_DEV,
    AVG_PREP_DAYS,
    AVG_MOED_GAP,
    MIN_MOED_GAP,
    DOUBLE_EXAM_DAYS,
    BUSIEST_WEEK_COUNT,
    MANDATORY_CONSEC,
    MAX_REST_DAYS,
    B2B_EXAM_INCIDENCE,
    DEPT_EXAM_CONCURRENCY,
    INSTRUCTOR_EXAM_GAP,
)

# Substrings (lower-cased) that point at each criterion, English + Hebrew.
_CRITERION_KEYWORDS: Dict[str, List[str]] = {
    MIN_MANDATORY_GAP: [
        "rest", "breathing", "recovery", "rest between", "days between mandatory",
        "מנוחה", "לנשום", "רווח בין חובה", "מרווח בין חובה",
    ],
    AVG_ALL_COURSES_GAP: [
        "spread", "spaced", "spacing", "spread out", "apart", "gaps", "breathing room",
        "מרווח", "מרווחים", "פיזור", "מפוזר", "רווחים", "מרוווח",
    ],
    ELECTIVE_CONFLICTS: [
        "conflict", "clash", "elective", "overlap", "collision",
        "התנגשות", "התנגשויות", "בחירה", "קונפליקט", "חפיפה", "חופשי",
    ],
    MANDATORY_SPAN: [
        "span", "window", "compact", "short", "tight", "concentrated", "period",
        "טווח", "חלון", "צפוף", "קצר", "מרוכז", "תקופה", "דחוס",
    ],
    MAX_EXAMS_PER_DAY: [
        "per day", "same day", "one day", "busy day", "load", "exams a day",
        "exam day", "exam days", "exams per day", "lightest day", "light day", "heavy day",
        "ביום", "באותו יום", "עומס", "ביום אחד", "מבחנים ביום", "בחינות ביום",
    ],
    GAP_STD_DEV: [
        "gap stddev", "gap variance", "gap uniformity", "uniform gaps",
        "סטיית תקן של רווחים", "אחידות",
    ],
    AVG_PREP_DAYS: [
        "prep", "preparation", "study time", "days to study",
        "הכנה", "זמן הכנה", "ללמוד",
    ],
    MAX_REST_DAYS: [
        "max rest", "max gap", "maximum spacing",
        "מרווח מקסימלי", "הכי הרבה מנוחה",
    ],
    B2B_EXAM_INCIDENCE: [
        "back to back", "back-to-back", "consecutive", "b2b",
        "עוקבים", "ימים עוקבים", "גב אל גב",
    ],
    DEPT_EXAM_CONCURRENCY: [
        "departmental concurrency", "department concurrency", "dept concurrency",
        "חפיפה מחלקתית", "מחלקה",
    ],
    INSTRUCTOR_EXAM_GAP: [
        "instructor gap", "professor gap", "lecturer gap", "faculty spacing",
        "מרווח מרצים", "מרצה", "פרופסור",
    ],
    AVG_MOED_GAP: [
        "average moed gap", "average exam gap", "average spacing",
        "מרווח ממוצע", "מרווח בחינות ממוצע",
    ],
    MIN_MOED_GAP: [
        "minimum moed gap", "minimum exam gap", "tightest moed spacing",
        "מרווח מינימלי", "מרווח בחינות מינימלי",
    ],
    
    DOUBLE_EXAM_DAYS: [
        "double exam days", "two exams in one day", "same day exams",
        "ימים עם שתי בחינות", "מבחנים באותו יום",
    ],
    BUSIEST_WEEK_COUNT: [
        "busiest week", "busiest week count", "most exams in a week",
        "שבוע עמוס ביותר", "השבוע הכי עמוס",
    ],
    MANDATORY_CONSEC: [
        "mandatory consecutive", "consecutive mandatory", "consecutive exams",
        "חובה עוקבות", "מבחנים עוקבים", "עוקבות",
    ],
}

_EMPHASIS_WORDS = [
    "mostly", "mainly", "primarily", "especially", "focus on", "above all", "most",
    "בעיקר", "בעקר", "דגש", "בדגש", "במיוחד", "הכי חשוב", "בעיקר לפי",
]

# Words that signal the number nearby is a count of groups (so "5" -> K=5).
_GROUP_WORDS = ["group", "groups", "family", "families", "cluster", "clusters",
                "קבוצ", "משפח", "אשכול"]

_EN_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_HE_NUMBERS = {
    "אחת": 1, "שתיים": 2, "שתי": 2, "שניים": 2, "שני": 2, "שלוש": 3, "שלושה": 3,
    "ארבע": 4, "ארבעה": 4, "חמש": 5, "חמישה": 5, "שש": 6, "שישה": 6,
    "שבע": 7, "שבעה": 7, "שמונה": 8, "תשע": 9, "תשעה": 9, "עשר": 10, "עשרה": 10,
}


_INTENT_PHRASES: Dict[str, Tuple[str, str]] = {
    MIN_MANDATORY_GAP:      ("rest between exams",                      "מנוחה בין בחינות"),
    AVG_ALL_COURSES_GAP:    ("even spacing",                            "מרווח אחיד בין בחינות"),
    ELECTIVE_CONFLICTS:     ("fewer elective clashes",                  "פחות התנגשויות בחירה"),
    MANDATORY_SPAN:         ("exam span control",                       "שליטה בפיזור הבחינות"),
    MAX_EXAMS_PER_DAY:      ("lighter exam days",                       "ימים עם פחות בחינות"),
    GAP_STD_DEV:            ("consistent gaps",                         "רווחים עקביים"),
    AVG_PREP_DAYS:          ("prep time before exams",                  "זמן הכנה לפני בחינות"),
    MAX_REST_DAYS:          ("rest windows",                            "חלונות מנוחה"),
    B2B_EXAM_INCIDENCE:     ("fewer back-to-back days",                 "פחות ימים עוקבים"),
    DEPT_EXAM_CONCURRENCY:  ("department load",                         "עומס מחלקתי"),
    INSTRUCTOR_EXAM_GAP:    ("instructor spacing",                      "מרווח למרצים"),
    AVG_MOED_GAP:           ("retake spacing",                          "מרווח בין מועדים"),
    MIN_MOED_GAP:           ("retake spacing",                          "מרווח בין מועדים"),
    DOUBLE_EXAM_DAYS:       ("no double-exam days",                     "בלי יומיים כפולים"),
    BUSIEST_WEEK_COUNT:     ("lighter weeks",                           "שבועות קלים יותר"),
    MANDATORY_CONSEC:       ("fewer consecutive mandatory days",        "פחות ימי חובה רצופים"),
}


class HeuristicRequestParser:
    """Maps a free-text clustering request onto a ClusterConfig by keywords."""

    def parse(self, text: str) -> Tuple[ClusterConfig, str]:
        raw = (text or "").strip()
        low = raw.lower()

        criteria = self._match_criteria(low)
        emphasised = self._first_match(low) if self._has_emphasis(low) else None
        k = self._match_k(low)

        weights: Dict[str, float] = {}
        if emphasised is not None:
            weights[emphasised] = 3.0
            if emphasised not in criteria:
                criteria.append(emphasised)

        kwargs = {}
        if criteria:
            kwargs["criteria"] = tuple(criteria)
        if weights:
            kwargs["weights"] = weights
        if k is not None:
            kwargs["k_mode"] = K_MODE_FIXED
            kwargs["k"] = k
        else:
            kwargs["k_mode"] = K_MODE_AUTO

        try:
            config = ClusterConfig(**kwargs)
        except ValueError:
            config = ClusterConfig.default()

        return config, self._interpretation(config, emphasised, k, raw)

    # ── matching helpers ─────────────────────────────────────────────────────

    def _match_criteria(self, low: str) -> List[str]:
        matched: List[str] = []
        for criterion, words in _CRITERION_KEYWORDS.items():
            if any(w in low for w in words):
                matched.append(criterion)
        return matched

    def _first_match(self, low: str):
        for criterion, words in _CRITERION_KEYWORDS.items():
            if any(w in low for w in words):
                return criterion
        return None

    def _has_emphasis(self, low: str) -> bool:
        return any(w in low for w in _EMPHASIS_WORDS)

    def _match_k(self, low: str):
        if not any(w in low for w in _GROUP_WORDS):
            return None
        # Only accept a digit that directly signals the number of groups.
        # Valid patterns: "into N", "divided into N", "N groups", "N families", etc.
        for m in re.finditer(
            r"(?:divided\s+into|into)\s+(\d+)"
            r"|(\d+)\s*(?:groups?|families|family|clusters?"
            r"|קבוצות|קבוצ\w*|משפחות|משפח\w*|אשכולות|אשכול\w*)",
            low,
        ):
            digit = next(g for g in m.groups() if g is not None)
            value = int(digit)
            if 2 <= value <= 20:
                return value
        # Spelled-out number word followed by a group word within 3 tokens.
        # Hebrew tokens may carry single-letter prefixes (ל ,כ ,ב ,מ …) so we
        # accept the number word as a suffix of the token; English requires
        # exact match to avoid false positives ("stone" ending in "one" etc.).
        tokens = low.split()
        for i, token in enumerate(tokens):
            window = tokens[i + 1 : i + 4]
            for word, value in _EN_NUMBERS.items():
                if token == word and any(gw in t for gw in _GROUP_WORDS for t in window):
                    return value
            for word, value in _HE_NUMBERS.items():
                if (token == word or token.endswith(word)) and any(
                    gw in t for gw in _GROUP_WORDS for t in window
                ):
                    return value
        return None

    # ── interpretation text ──────────────────────────────────────────────────

    def _is_hebrew(self, text: str) -> bool:
        return any('א' <= c <= 'ת' for c in text)

    def _interpretation(self, config: ClusterConfig, emphasised, k, raw: str = "") -> str:
        from src.logic.clustering.ClusteringScorer import EXTENDED_CRITERIA
        he = self._is_hebrew(raw)

        k_part = (
            f"ל-{config.k} קבוצות"
            if config.k_mode == K_MODE_FIXED and config.k
            else "עם מספר קבוצות אוטומטי"
        )
        k_tail = (
            f"into {config.k} families"
            if config.k_mode == K_MODE_FIXED and config.k
            else "with an automatic number of families"
        )

        def _phrase(cid: str) -> str:
            pair = _INTENT_PHRASES.get(cid)
            if pair is None:
                return CriterionDisplay.label(cid)
            return pair[1] if he else pair[0]

        if tuple(config.criteria) == tuple(EXTENDED_CRITERIA) and not config.weights:
            if he:
                return f"קיבוץ לפי כל הקריטריונים, {k_part}"
            return f"Grouping by overall schedule quality, {k_tail}."

        if emphasised is not None:
            if he:
                return f"קיבוץ בעיקר לפי {_phrase(emphasised)}, {k_part}"
            return f"Grouping mainly by {_phrase(emphasised)}, {k_tail}."

        phrases = [_phrase(c) for c in config.criteria]
        if len(phrases) > 3:
            if he:
                shown = ", ".join(phrases[:3]) + " ועוד גורמים"
            else:
                shown = ", ".join(phrases[:3]) + " and more"
        else:
            shown = ", ".join(phrases)

        if he:
            return f"קיבוץ לפי {shown}, {k_part}"
        return f"Grouping by {shown}, {k_tail}."
