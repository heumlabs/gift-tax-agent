"""Tests for request/response schemas."""

from ai.schemas import ChatRequest, ChatResponse


def test_chat_request_basic():
    """Test ChatRequest with normal content."""
    req = ChatRequest(content="Hello")
    assert req.content == "Hello"
    assert req.metadata is None


def test_chat_request_strips_whitespace():
    """Test ChatRequest strips leading/trailing whitespace."""
    req = ChatRequest(content="  Hello  ")
    assert req.content == "Hello"


def test_chat_request_allows_empty():
    """Test ChatRequest allows empty content (validation removed)."""
    req = ChatRequest(content="")
    assert req.content == ""


def test_chat_request_with_metadata():
    """Test ChatRequest with custom metadata."""
    metadata = {"session_id": "123"}
    req = ChatRequest(content="Test", metadata=metadata)
    assert req.metadata == metadata


def test_chat_response_defaults():
    """Test ChatResponse has proper default values."""
    resp = ChatResponse(content="Answer")
    assert resp.content == "Answer"
    assert resp.citations == []
    assert resp.calculation is None
    assert resp.clarifying_context == []
    assert resp.assumptions == []
    assert resp.missing_parameters == []
    assert resp.exceptions == []
    assert resp.recommendations == []
    assert resp.tool_calls == []


def test_chat_response_with_citations():
    """Test ChatResponse with citations."""
    citations = [{"source_id": 1, "law_name": "증여세법"}]
    resp = ChatResponse(content="Answer", citations=citations)
    assert resp.citations == citations
