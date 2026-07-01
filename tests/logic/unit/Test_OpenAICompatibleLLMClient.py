"""
Test suite for OpenAICompatibleLLMClient.

Scope   : Network interaction, configuration parsing, and error handling for the LLM API.
          Validates that missing keys raise RuntimeErrors, HTTP timeouts/errors are properly
          surfaced or retried (429), and valid JSON responses are cleanly parsed.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-LLM-001..006
"""
import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.logic.clustering.llm.OpenAICompatibleLLMClient import OpenAICompatibleLLMClient


# ===========================================================================
# TC-LLM-001: from_env correctly extracts the configuration from environment
# variables or falls back to standard defaults securely.
# ===========================================================================
@patch.dict(os.environ, {
    "CLUSTER_LLM_API_KEY": "test-key-123",
    "CLUSTER_LLM_BASE_URL": "https://api.custom.com",
    "CLUSTER_LLM_MODEL": "test-model-456",
    "CLUSTER_LLM_TIMEOUT": "5.5"
}, clear=True)
def test_from_env_parses_custom_config_correctly():
    # Arrange / Act
    client = OpenAICompatibleLLMClient.from_env()

    # Assert
    assert client.is_available() is True
    assert client._api_key == "test-key-123"
    assert client._base_url == "https://api.custom.com"
    assert client._model == "test-model-456"
    assert client._timeout == 5.5


# ===========================================================================
# TC-LLM-002: from_env falls back to standard defaults (no key -> off, OpenAI
# base URL, gpt-4o-mini, 8.0s timeout) when no CLUSTER_LLM_* vars are set.
# ===========================================================================
@patch.dict(os.environ, {}, clear=True)
def test_from_env_uses_defaults_when_missing():
    # Arrange / Act
    client = OpenAICompatibleLLMClient.from_env()

    # Assert
    assert client.is_available() is False
    assert client._api_key == ""
    assert client._base_url == "https://api.openai.com/v1"
    assert client._model == "gpt-4o-mini"
    assert client._timeout == 8.0


# ===========================================================================
# TC-LLM-003: complete() successfully parses a valid OpenAI-style JSON output
# ===========================================================================
@patch("urllib.request.urlopen")
def test_complete_returns_content_on_success(mock_urlopen):
    # Arrange
    client = OpenAICompatibleLLMClient(api_key="valid")

    mock_response = MagicMock()
    # Create a realistic JSON structure that an OpenAI compatible API returns
    valid_payload = json.dumps({
        "choices": [{"message": {"content": "Expected Summary Output"}}]
    }).encode("utf-8")
    mock_response.read.return_value = valid_payload
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Act
    result = client.complete("System prompt", "User prompt")

    # Assert
    assert result == "Expected Summary Output"
    mock_urlopen.assert_called_once()


# ===========================================================================
# TC-LLM-004: complete() immediately raises a RuntimeError if the client
# is invoked without an API key (failsafe).
# ===========================================================================
def test_complete_raises_runtime_error_if_unavailable():
    # Arrange
    client = OpenAICompatibleLLMClient(api_key="")

    # Act / Assert
    with pytest.raises(RuntimeError, match="LLM client is not configured"):
        client.complete("System", "User")


# ===========================================================================
# TC-LLM-005: complete() automatically retries once if a 429 Too Many Requests
# is received, and raises the HTTPError if the second attempt also fails.
# ===========================================================================
@patch("urllib.request.urlopen")
@patch("time.sleep")
def test_complete_retries_once_on_429(mock_sleep, mock_urlopen):
    # Arrange
    client = OpenAICompatibleLLMClient(api_key="valid")
    error_429 = urllib.error.HTTPError(url="", code=429, msg="Too Many Requests", hdrs={}, fp=None)
    mock_urlopen.side_effect = [error_429, error_429]

    # Act / Assert
    with pytest.raises(urllib.error.HTTPError):
        client.complete("System", "User")

    # Verify that it tried exactly twice and slept in between
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once_with(1.5)


# ===========================================================================
# TC-LLM-006: complete() surfaces a URLError immediately when a timeout occurs
# ===========================================================================
@patch("urllib.request.urlopen")
def test_complete_raises_url_error_on_timeout(mock_urlopen):
    # Arrange
    client = OpenAICompatibleLLMClient(api_key="valid")
    timeout_error = urllib.error.URLError("Request timed out")
    mock_urlopen.side_effect = timeout_error

    # Act / Assert
    with pytest.raises(urllib.error.URLError):
        client.complete("System", "User")
