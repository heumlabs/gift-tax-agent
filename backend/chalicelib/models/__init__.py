"""Models package"""

from .database import Client, Session, Message, LawSource, KnowledgeSource, TaxRuleConfig
from .api import (
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    SessionListResponse,
    MessageResponse,
    MessageCreate,
    MessageListResponse,
    AssistantMessageResponse,
    ErrorDetail,
    ErrorResponse,
)

__all__ = [
    # Database models
    "Client",
    "Session",
    "Message",
    "LawSource",
    "KnowledgeSource",
    "TaxRuleConfig",
    # API models
    "SessionCreate",
    "SessionResponse",
    "SessionUpdate",
    "SessionListResponse",
    "MessageResponse",
    "MessageCreate",
    "MessageListResponse",
    "AssistantMessageResponse",
    "ErrorDetail",
    "ErrorResponse",
]
