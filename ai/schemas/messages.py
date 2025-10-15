from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ChatRequest:
    """Minimal request payload for the chat pipeline."""

    content: str
    metadata: Optional[Dict[str, object]] = None

    def __post_init__(self) -> None:
        if isinstance(self.content, str):
            self.content = self.content.strip()


@dataclass
class ChatResponse:
    content: str
    citations: List[Dict[str, object]] = field(default_factory=list)
    calculation: Optional[Dict[str, object]] = None
    clarifying_context: List[Dict[str, object]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    missing_parameters: List[Dict[str, Any]] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
