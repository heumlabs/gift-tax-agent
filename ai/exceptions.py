"""Custom exception hierarchy for the AI chat prototype."""

from typing import Any, Dict, Optional


class ChatPipelineError(RuntimeError):
    """Base error for chat pipeline related failures."""


class GeminiClientError(ChatPipelineError):
    """Raised when the Gemini REST API is unreachable or returns an error."""

    def __init__(self, status_code: int, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class ValidationError(ChatPipelineError):
    """Raised when request validation fails (e.g., empty content)."""
