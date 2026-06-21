"""Natural-language → clustering-config translation.

Turns a free-text request ("group by the lightest exam days, 4 groups") into a
validated ``ClusterConfig`` that the existing engine runs unchanged. Tries an LLM
first (optional, configured by environment variables) and always falls back to a
dependency-free keyword parser, so the feature works for everyone with zero setup.
"""
from src.logic.clustering.llm.ClusterRequestTranslator import (
    ClusterRequestTranslator,
    TranslationResult,
)
from src.logic.clustering.llm.HeuristicRequestParser import HeuristicRequestParser
from src.logic.clustering.llm.ILLMClient import ILLMClient
from src.logic.clustering.llm.OpenAICompatibleLLMClient import OpenAICompatibleLLMClient

__all__ = [
    "ClusterRequestTranslator",
    "TranslationResult",
    "HeuristicRequestParser",
    "ILLMClient",
    "OpenAICompatibleLLMClient",
]
