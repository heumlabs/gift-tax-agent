"""
API 요청/응답 모델 정의 (Pydantic)

연관 문서: docs/prd_detail/api-spec.md
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ===== Session Models =====


class SessionCreate(BaseModel):
    """세션 생성 요청"""

    pass  # Empty body


class SessionResponse(BaseModel):
    """세션 응답"""

    id: str
    title: str
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class SessionUpdate(BaseModel):
    """세션 제목 수정 요청"""

    title: str


class SessionListResponse(BaseModel):
    """세션 목록 응답"""

    sessions: List[SessionResponse]
    next_cursor: Optional[str] = Field(None, alias="nextCursor")

    class Config:
        populate_by_name = True


# ===== Message Models =====


class MessageResponse(BaseModel):
    """메시지 응답"""

    id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class MessageCreate(BaseModel):
    """사용자 메시지 생성 요청"""

    content: str


class MessageListResponse(BaseModel):
    """메시지 목록 응답"""

    messages: List[MessageResponse]
    next_cursor: Optional[str] = Field(None, alias="nextCursor")

    class Config:
        populate_by_name = True


class AssistantMessageResponse(BaseModel):
    """AI 응답 메시지 (POST /sessions/{id}/messages)"""

    assistant_message: MessageResponse = Field(alias="assistantMessage")

    class Config:
        populate_by_name = True


# ===== Error Models =====


class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """에러 응답"""

    error: ErrorDetail
