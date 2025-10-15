"""Tests for service entry point."""

from unittest.mock import AsyncMock, patch

import pytest

from ai.exceptions import ChatPipelineError, GeminiClientError
from ai.schemas import ChatResponse
from ai.service import generate_assistant_message


@pytest.fixture
def mock_pipeline():
    """Mock ChatPipeline for testing."""
    with patch("ai.service._get_pipeline") as mock_get:
        pipeline_instance = mock_get.return_value
        pipeline_instance.run = AsyncMock()
        yield pipeline_instance


def test_generate_assistant_message_success(mock_pipeline):
    """Test successful message generation."""
    mock_pipeline.run.return_value = ChatResponse(content="Test response")

    result = generate_assistant_message(content="Hello")

    assert result["role"] == "assistant"
    assert result["content"] == "Test response"
    assert "id" in result
    assert "createdAt" in result
    assert "metadata" in result
    assert result["metadata"]["citations"] == []


def test_generate_assistant_message_with_metadata(mock_pipeline):
    """Test message generation preserves metadata."""
    response = ChatResponse(
        content="Answer",
        citations=[{"source_id": 1}],
        assumptions=["거주자 간 증여"]
    )
    mock_pipeline.run.return_value = response

    result = generate_assistant_message(content="Question", metadata={"session": "123"})

    assert result["metadata"]["citations"] == [{"source_id": 1}]
    assert result["metadata"]["assumptions"] == ["거주자 간 증여"]


def test_generate_assistant_message_gemini_error(mock_pipeline):
    """Test that GeminiClientError is propagated."""
    mock_pipeline.run.side_effect = GeminiClientError(status_code=429, message="Rate limit")

    with pytest.raises(GeminiClientError) as exc_info:
        generate_assistant_message(content="Test")

    assert exc_info.value.status_code == 429


def test_generate_assistant_message_pipeline_error(mock_pipeline):
    """Test that ChatPipelineError is propagated."""
    mock_pipeline.run.side_effect = ChatPipelineError("Pipeline failed")

    with pytest.raises(ChatPipelineError):
        generate_assistant_message(content="Test")


def test_generate_assistant_message_unexpected_error(mock_pipeline):
    """Test that unexpected errors are wrapped in ChatPipelineError."""
    mock_pipeline.run.side_effect = RuntimeError("Unexpected")

    with pytest.raises(ChatPipelineError) as exc_info:
        generate_assistant_message(content="Test")

    assert "Unexpected" in str(exc_info.value)
