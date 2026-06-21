"""Translate a free-text clustering request into a validated ClusterConfig.

Order of attempts (each one degrades gracefully to the next):
  1. LLM — if a client is configured, ask it to emit a small JSON config.
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
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.logic.clustering.ClusterConfig import ClusterConfig, K_MODE_AUTO, K_MODE_FIXED
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.comparators.ScheduleScorer import ALL_CRITERIA

_SYSTEM_PROMPT = """You translate a student's plain-language request into a JSON \
configuration for clustering exam schedules. The schedules are scored on five \
criteria (use these exact ids):

- MIN_MANDATORY_GAP: minimum days between two mandatory exams (higher = more rest).
- AVG_ALL_COURSES_GAP: average days between consecutive exams (higher = more spread out).
- ELECTIVE_CONFLICTS: number of elective-exam clashes (lower = fewer clashes).
- MANDATORY_SPAN: total days the mandatory exams stretch across (lower = more compact).
- MAX_EXAMS_PER_DAY: the most exams on any single day (lower = lighter days).

Output ONLY a JSON object with this shape (no prose, no code fences):
{
  "criteria": [subset of the five ids; use all five for a general request],
  "weights": {"<id>": <number >= 1>},   // optional, to emphasise a criterion
  "k_mode": "auto" | "fixed",
  "k": <integer>,                         // only when k_mode is "fixed"
  "explanation": "<one short sentence, in the user's language>"
}
If the request does not mention a number of groups, use "k_mode": "auto"."""

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
            except Exception:
                pass  # fall through to the keyword parser

        # 2. Keyword parser (always available).
        config, interpretation = self._parser.parse(request)
        return TranslationResult(config, interpretation, "heuristic")

    # ── LLM JSON handling ────────────────────────────────────────────────────

    def _config_from_llm(self, raw: str) -> Tuple[ClusterConfig, str]:
        data = self._extract_json(raw)

        kwargs = {}

        known = set(ALL_CRITERIA)
        criteria = [c for c in (data.get("criteria") or []) if c in known]
        if criteria:
            kwargs["criteria"] = tuple(dict.fromkeys(criteria))  # de-dupe, keep order

        weights_in = data.get("weights") or {}
        weights = {}
        for cid, w in weights_in.items():
            if cid in known:
                try:
                    weights[cid] = float(w)
                except (TypeError, ValueError):
                    continue
        if weights:
            kwargs["weights"] = weights

        k_mode = data.get("k_mode")
        if k_mode == K_MODE_FIXED:
            kwargs["k_mode"] = K_MODE_FIXED
            kwargs["k"] = int(data.get("k"))
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
