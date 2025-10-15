"""Shared pytest configuration and fixtures."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for all tests."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key-for-testing"}):
        yield
