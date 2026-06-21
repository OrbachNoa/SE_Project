"""Interface for a minimal chat LLM client.

The translator depends only on this tiny contract, so any provider (OpenAI,
Groq, a local server, ...) can be plugged in by implementing ``complete``. A
client also reports whether it is *available* (configured), so the translator can
silently skip the LLM and use the keyword parser when no key is set.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ILLMClient(ABC):
    """A single-turn chat completion with a system and a user message."""

    @abstractmethod
    def is_available(self) -> bool:
        """True when the client is configured (e.g. an API key is present)."""
        raise NotImplementedError

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's text reply. May raise on network/HTTP errors."""
        raise NotImplementedError
