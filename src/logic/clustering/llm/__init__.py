"""Natural-language → clustering-config translation.

Turns a free-text request ("group by the lightest exam days, 4 groups") into a
validated ``ClusterConfig`` that the existing engine runs unchanged. Tries an LLM
first when one is configured; if no LLM is configured at all, falls back to a
dependency-free keyword parser so the feature still works with zero setup. If an
LLM *is* configured but fails or times out, that failure is raised as
``ClusterTranslationError`` instead of silently falling back.
"""
from src.logic.clustering.llm.ClusterRequestTranslator import (
    ClusterRequestTranslator,
    TranslationResult,
)
from src.logic.clustering.llm.ClusterTranslationError import ClusterTranslationError
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.clustering.llm.OpenAICompatibleLLMClient import OpenAICompatibleLLMClient

__all__ = [
    "ClusterRequestTranslator",
    "TranslationResult",
    "ClusterTranslationError",
    "HeuristicRequestParser",
    "ILLMClient",
    "OpenAICompatibleLLMClient",
]
