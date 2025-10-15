"""Tests for configuration."""

import os
from unittest.mock import patch

import pytest

from ai.config import GeminiSettings


def test_gemini_settings_from_env():
    """Test GeminiSettings loads from environment variables."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}):
        settings = GeminiSettings.from_env()
        assert settings.api_key == "test-key-123"
        assert settings.model == "gemini-2.5-flash"
        assert settings.request_timeout == 30.0


def test_gemini_settings_custom_model():
    """Test GeminiSettings with custom model name."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key", "GEMINI_MODEL": "gemini-2.0-pro"}):
        settings = GeminiSettings.from_env()
        assert settings.model == "gemini-2.0-pro"


def test_gemini_settings_custom_timeout():
    """Test GeminiSettings with custom timeout."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key", "GEMINI_TIMEOUT_SECONDS": "60"}):
        settings = GeminiSettings.from_env()
        assert settings.request_timeout == 60.0


def test_gemini_settings_missing_api_key():
    """Test GeminiSettings raises error when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY is not set"):
            GeminiSettings.from_env()


def test_gemini_settings_endpoint():
    """Test endpoint URL generation."""
    settings = GeminiSettings(api_key="test", model="gemini-2.5-flash")
    assert settings.endpoint == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def test_gemini_settings_endpoint_with_models_prefix():
    """Test endpoint URL when model already has 'models/' prefix."""
    settings = GeminiSettings(api_key="test", model="models/gemini-pro")
    assert settings.endpoint == "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
