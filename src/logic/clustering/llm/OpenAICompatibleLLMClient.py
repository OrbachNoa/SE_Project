"""A provider-agnostic LLM client for any OpenAI-compatible chat API.

Configured entirely through environment variables, so no key ever lives in the
code and any compatible provider works by pointing the base URL at it:

    CLUSTER_LLM_API_KEY    required to enable the LLM (otherwise it stays "off")
    CLUSTER_LLM_BASE_URL   default "https://api.openai.com/v1"
    CLUSTER_LLM_MODEL      default "gpt-4o-mini"
    CLUSTER_LLM_TIMEOUT    request timeout in seconds (default 20)

Free options that expose an OpenAI-compatible endpoint (e.g. Groq) work by setting
CLUSTER_LLM_BASE_URL + CLUSTER_LLM_MODEL to that provider. The HTTP call uses only
the standard library, so there is no extra dependency to install.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from src.logic.clustering.llm.ILLMClient import ILLMClient

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT = 20.0


class OpenAICompatibleLLMClient(ILLMClient):
    """Calls ``/chat/completions`` on any OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key or ""
        self._base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self._model = model or _DEFAULT_MODEL
        self._timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLMClient":
        """Build a client from the CLUSTER_LLM_* environment variables."""
        try:
            timeout = float(os.environ.get("CLUSTER_LLM_TIMEOUT", _DEFAULT_TIMEOUT))
        except ValueError:
            timeout = _DEFAULT_TIMEOUT
        return cls(
            api_key=os.environ.get("CLUSTER_LLM_API_KEY"),
            base_url=os.environ.get("CLUSTER_LLM_BASE_URL", _DEFAULT_BASE_URL),
            model=os.environ.get("CLUSTER_LLM_MODEL", _DEFAULT_MODEL),
            timeout=timeout,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("LLM client is not configured (no API key)")

        body = json.dumps({
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")

        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "ExamScheduler/34.0",
            },
        )

        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                # Standard OpenAI-compatible shape: choices[0].message.content.
                return payload["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    time.sleep(1.5)
                    continue
                raise
